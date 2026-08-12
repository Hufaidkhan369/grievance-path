"""Analytics queries for the dashboard."""
from __future__ import annotations

from datetime import datetime, timedelta

from ..database import fetch_all, fetch_one


def overview() -> dict:
    total = fetch_one("SELECT COUNT(*) AS c FROM complaints")["c"]
    resolved = fetch_one("SELECT COUNT(*) AS c FROM complaints WHERE status IN ('RESOLVED','CLOSED')")["c"]
    pending = fetch_one("SELECT COUNT(*) AS c FROM complaints WHERE status IN ('PENDING','IN_PROGRESS')")["c"]
    urgent = fetch_one("SELECT COUNT(*) AS c FROM complaints WHERE priority = 'URGENT'")["c"]
    departments = fetch_one("SELECT COUNT(*) AS c FROM departments")["c"]
    users = fetch_one("SELECT COUNT(*) AS c FROM users")["c"]
    fb = fetch_one("SELECT COUNT(*) AS n, COALESCE(AVG(rating), 0) AS avg FROM feedback")
    return {
        "total": total,
        "resolved": resolved,
        "pending": pending,
        "urgent": urgent,
        "departments": departments,
        "users": users,
        "feedback_count": fb["n"],
        "avg_rating": round(fb["avg"], 2),
        "resolution_rate": round(resolved / total * 100, 1) if total else 0.0,
    }


def by_department() -> list[dict]:
    return fetch_all(
        """SELECT d.id, d.code, d.name, d.color,
                  COUNT(c.id) AS total,
                  SUM(CASE WHEN c.status IN ('RESOLVED','CLOSED') THEN 1 ELSE 0 END) AS resolved
           FROM departments d LEFT JOIN complaints c ON c.department_id = d.id
           GROUP BY d.id ORDER BY total DESC"""
    )


def by_status() -> list[dict]:
    return fetch_all(
        "SELECT status, COUNT(*) AS total FROM complaints GROUP BY status ORDER BY total DESC"
    )


def by_priority() -> list[dict]:
    return fetch_all(
        "SELECT priority, COUNT(*) AS total FROM complaints GROUP BY priority ORDER BY total DESC"
    )


def trend(days: int = 14) -> list[dict]:
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    rows = fetch_all(
        """SELECT date(created_at) AS day, COUNT(*) AS total
           FROM complaints WHERE date(created_at) >= ? GROUP BY day ORDER BY day""",
        (since,),
    )
    by_day = {r["day"]: r["total"] for r in rows}
    out = []
    for i in range(days - 1, -1, -1):
        d = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        out.append({"day": d, "total": by_day.get(d, 0)})
    return out


def routing_methods() -> list[dict]:
    return fetch_all(
        "SELECT routing_method, COUNT(*) AS total FROM complaints GROUP BY routing_method ORDER BY total DESC"
    )


def low_confidence() -> list[dict]:
    return fetch_all(
        """SELECT c.tracking_id, c.title, c.department_confidence, d.name AS department_name
           FROM complaints c LEFT JOIN departments d ON d.id = c.department_id
           WHERE c.department_confidence < 0.35 ORDER BY c.department_confidence ASC LIMIT 20"""
    )
