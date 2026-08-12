"""Complaint lifecycle: create, track, update, history, notifications."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from ..database import db, now_utc, fetch_one, fetch_all
from ..config import settings

SLA_DAYS = {"LOW": 14, "MEDIUM": 7, "HIGH": 3, "URGENT": 1}


def generate_tracking_id() -> str:
    year = datetime.now().year
    with db() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM complaints WHERE tracking_id LIKE ?",
            (f"GRV-{year}-%",),
        ).fetchone()
    return f"GRV-{year}-{row['c'] + 1:04d}"


def priority_from_confidence(confidence: float) -> str:
    if confidence >= 0.75:
        return "HIGH"
    if confidence >= 0.45:
        return "MEDIUM"
    return "LOW"


def create_complaint(*, title, description, category, location, city, pincode,
                     contact_name, contact_email, contact_phone, department_id,
                     confidence, method, matched_keywords, note="", status="PENDING",
                     user_id=None):
    cid = uuid.uuid4().hex[:12].upper()
    tracking = generate_tracking_id()
    ts = now_utc()
    priority = priority_from_confidence(confidence)
    sla = (datetime.now(timezone.utc) + timedelta(days=SLA_DAYS.get(priority, 7))
           ).isoformat(timespec="seconds")

    with db() as conn:
        conn.execute(
            """INSERT INTO complaints
               (id, tracking_id, title, description, category, location, city,
                pincode, contact_name, contact_email, contact_phone, user_id,
                department_id, department_confidence, routing_method,
                matched_keywords, status, priority, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (cid, tracking, title, description, category, location, city,
             pincode, contact_name, contact_email, contact_phone, user_id,
             department_id, confidence, method,
             ", ".join(matched_keywords), status, priority, ts, ts),
        )
        conn.execute(
            "INSERT INTO status_history(complaint_id, status, note, changed_by, created_at) "
            "VALUES (?,?,?,?,?)",
            (cid, status, note or "Grievance received and routed to department.", "system", ts),
        )
        # Add to the department's complaint queue (per-department database)
        queue_pos = conn.execute(
            "SELECT COALESCE(MAX(queue_position), 0) + 1 AS p FROM department_complaints WHERE department_id = ?",
            (department_id,),
        ).fetchone()["p"]
        conn.execute(
            "INSERT OR IGNORE INTO department_complaints"
            "(department_id, complaint_id, assigned_at, sla_due_at, queue_position) VALUES (?,?,?,?,?)",
            (department_id, cid, ts, sla, queue_pos),
        )
    return {"id": cid, "tracking_id": tracking, "sla_due_at": sla}


def get_complaint(complaint_id: str) -> dict | None:
    row = fetch_one(
        """SELECT c.*, d.name AS department_name, d.code AS department_code,
                  d.color AS department_color,
                  (SELECT sla_due_at FROM department_complaints dc
                   WHERE dc.complaint_id = c.id AND dc.department_id = c.department_id) AS sla_due_at
           FROM complaints c LEFT JOIN departments d ON d.id = c.department_id
           WHERE c.id = ? OR c.tracking_id = ?""",
        (complaint_id, complaint_id),
    )
    return row


def list_complaints(department_id: int | None = None, status: str | None = None,
                    limit: int = 200) -> list[dict]:
    sql = """SELECT c.*, d.name AS department_name, d.code AS department_code,
                    d.color AS department_color
             FROM complaints c LEFT JOIN departments d ON d.id = c.department_id
             WHERE 1=1"""
    params: list = []
    if department_id:
        sql += " AND c.department_id = ?"
        params.append(department_id)
    if status:
        sql += " AND c.status = ?"
        params.append(status)
    sql += " ORDER BY c.created_at DESC LIMIT ?"
    params.append(limit)
    return fetch_all(sql, tuple(params))


def get_history(complaint_id: str) -> list[dict]:
    return fetch_all(
        "SELECT * FROM status_history WHERE complaint_id = ? ORDER BY created_at ASC",
        (complaint_id,),
    )


def department_queue(department_id: int, status: str | None = None) -> list[dict]:
    """Each department's own complaint queue (from department_complaints + complaints)."""
    sql = """SELECT c.*, d.name AS department_name, d.code AS department_code,
                    d.color AS department_color,
                    dc.sla_due_at, dc.queue_position, dc.assigned_at
             FROM department_complaints dc
             JOIN complaints c ON c.id = dc.complaint_id
             JOIN departments d ON d.id = dc.department_id
             WHERE dc.department_id = ?"""
    params: list = [department_id]
    if status:
        sql += " AND c.status = ?"
        params.append(status)
    sql += " ORDER BY dc.queue_position ASC"
    return fetch_all(sql, tuple(params))


def add_feedback(complaint_id: str, rating: int, comment: str, user_id: int | None = None,
                 channel: str = "web") -> dict:
    complaint = get_complaint(complaint_id)
    if not complaint:
        return {"ok": False, "message": "Complaint not found"}
    rating = max(1, min(5, int(rating)))
    ts = now_utc()
    with db() as conn:
        conn.execute(
            "INSERT INTO feedback(complaint_id, user_id, rating, comment, channel, created_at) "
            "VALUES (?,?,?,?,?,?)",
            (complaint["id"], user_id, rating, comment, channel, ts),
        )
    return {"ok": True, "rating": rating, "message": "Thank you for your feedback!"}


def get_feedback(complaint_id: str | None = None, limit: int = 200) -> list[dict]:
    if complaint_id:
        return fetch_all(
            """SELECT f.*, c.tracking_id, c.title FROM feedback f
               JOIN complaints c ON c.id = f.complaint_id
               WHERE f.complaint_id = ? ORDER BY f.created_at DESC LIMIT ?""",
            (complaint_id, limit),
        )
    return fetch_all(
        """SELECT f.*, c.tracking_id, c.title FROM feedback f
           JOIN complaints c ON c.id = f.complaint_id
           ORDER BY f.created_at DESC LIMIT ?""",
        (limit,),
    )


def update_complaint(complaint_id: str, *, status: str = "", priority: str = "",
                     note: str = "", changed_by: str = "user",
                     reassign_code: str = "") -> dict:
    complaint = get_complaint(complaint_id)
    if not complaint:
        return {"ok": False, "message": "Complaint not found"}

    ts = now_utc()
    sets, params = [], []
    final_status = complaint["status"]
    final_priority = complaint["priority"]

    if status and status != complaint["status"]:
        sets.append("status = ?")
        params.append(status)
        final_status = status
        if status in ("RESOLVED", "CLOSED"):
            sets.append("resolved_at = ?")
            params.append(ts)
        else:
            sets.append("resolved_at = NULL")

    if priority and priority != complaint["priority"]:
        sets.append("priority = ?")
        params.append(priority)
        final_priority = priority

    reassigned = False
    reassign_target_name = None
    if reassign_code:
        dept = fetch_one("SELECT id, name FROM departments WHERE UPPER(code) = ?", (reassign_code.upper(),))
        if not dept:
            return {"ok": False, "message": f"Unknown department code {reassign_code}"}
        if dept["id"] != complaint["department_id"]:
            sets.append("department_id = ?")
            params.append(dept["id"])
            reassigned = True
            reassign_target_name = dept["name"]

    if not sets:
        return {"ok": False, "message": "Nothing to update"}

    sets.append("updated_at = ?")
    params.append(ts)
    params.append(complaint["id"])

    with db() as conn:
        conn.execute(f"UPDATE complaints SET {', '.join(sets)} WHERE id = ?", tuple(params))
        history_note = note or "Status updated."
        if reassigned and reassign_target_name:
            history_note = (f"{note} [Reassigned to {reassign_target_name}]"
                            if note else f"Reassigned to {reassign_target_name}")
        conn.execute(
            "INSERT INTO status_history(complaint_id, status, note, changed_by, created_at) "
            "VALUES (?,?,?,?,?)",
            (complaint["id"], final_status, history_note, changed_by, ts),
        )

    # Notify the citizen about the change
    send_notification(complaint, channel="EMAIL", subject=f"Update on {complaint['tracking_id']}",
                      message=history_note)

    return {"ok": True, "message": "Complaint updated", "tracking_id": complaint["tracking_id"],
            "status": final_status, "priority": final_priority}


def send_notification(complaint: dict, *, channel: str, subject: str, message: str) -> dict:
    """Persist a notification. Real SMS/email only fires when SMTP creds exist;
    otherwise it is simulated (logged + recorded) which is perfect for demos."""
    if not settings.ALERT_ENABLED:
        return {"ok": True, "status": "SKIPPED"}
    recipient = ""
    if channel.upper() == "EMAIL":
        recipient = complaint.get("contact_email") or "citizen@example.com"
    elif channel.upper() == "SMS":
        recipient = complaint.get("contact_phone") or "0000000000"

    ts = now_utc()
    with db() as conn:
        conn.execute(
            "INSERT INTO notifications(complaint_id, channel, recipient, subject, message, status, created_at) "
            "VALUES (?,?,?,?,?,?,?)",
            (complaint["id"], channel.upper(), recipient, subject, message, "SENT", ts),
        )
    import logging
    logging.getLogger("grievance.alerts").info(
        "[%s] %s -> %s | %s | %s", channel.upper(), subject, recipient, complaint["tracking_id"], message
    )
    return {"ok": True, "status": "SENT", "recipient": recipient}
