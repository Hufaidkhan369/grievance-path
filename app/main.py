"""GrievancePath — Smart India Hackathon grievance routing system.

Citizens describe their complaint in their own words; the engine routes it to
the right department automatically (keyword classifier + optional ML/LLM).
"""
from __future__ import annotations

import logging
import secrets
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .database import init_db, fetch_all, fetch_one, now_utc
from .routing.service import router
from .services import analytics
from .services.complaint import (
    create_complaint, get_complaint, get_history, list_complaints, update_complaint,
    department_queue, add_feedback, get_feedback,
)
from .services.users import register_user, login_user, list_users
from .services.seed import seed, seed_demo_complaints
from .schemas import ComplaintIn, ComplaintUpdate, FeedbackIn, UserIn, UserLogin

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("grievance")

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title=settings.APP_NAME, version="1.0.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

# Simple in-memory demo session tokens: token -> role
SESSIONS: dict[str, dict] = {}


def _page(name: str) -> FileResponse:
    return FileResponse(STATIC_DIR / name)


def _new_session(role: str, dept_id: int | None = None, user_id: int | None = None) -> str:
    token = secrets.token_hex(16)
    SESSIONS[token] = {"role": role, "department_id": dept_id, "user_id": user_id}
    return token


def _auth(request: Request, allowed: list[str] | None = None) -> dict | None:
    token = request.headers.get("authorization", "").replace("Bearer ", "")
    sess = SESSIONS.get(token)
    if not sess:
        return None
    if allowed and sess["role"] not in allowed:
        return None
    return sess


# ---------------------------------------------------------------- pages
@app.get("/", include_in_schema=False)
async def index():
    return _page("index.html")


@app.get("/department", include_in_schema=False)
async def dept_page():
    return _page("department.html")


@app.get("/admin", include_in_schema=False)
async def admin_page():
    return _page("admin.html")


@app.get("/analytics", include_in_schema=False)
async def analytics_page():
    return _page("analytics.html")


@app.get("/health")
async def health():
    return {"ok": True, "app": settings.APP_NAME, "llm_enabled": router.llm.enabled,
            "ml_enabled": router.ml.available}


# ---------------------------------------------------------------- auth
@app.post("/api/login")
async def login(payload: dict):
    role = (payload.get("role") or "").lower()
    password = payload.get("password") or ""
    if role == "admin":
        if password == settings.ADMIN_PASSWORD:
            return {"ok": True, "token": _new_session("admin"), "role": "admin"}
        return JSONResponse({"ok": False, "message": "Wrong admin password"}, 401)
    if role == "department":
        code = (payload.get("code") or "").upper()
        if password != settings.DEPT_PASSWORD:
            return JSONResponse({"ok": False, "message": "Wrong department password"}, 401)
        dept = fetch_one("SELECT * FROM departments WHERE UPPER(code) = ?", (code,))
        if not dept:
            return JSONResponse({"ok": False, "message": f"Unknown department {code}"}, 404)
        return {"ok": True, "token": _new_session("department", dept["id"]),
                "role": "department", "department": dept}
    return JSONResponse({"ok": False, "message": "Unknown role"}, 400)


@app.post("/api/logout")
async def logout(request: Request):
    token = request.headers.get("authorization", "").replace("Bearer ", "")
    SESSIONS.pop(token, None)
    return {"ok": True}


# ---------------------------------------------------------------- citizen
@app.get("/api/departments")
async def departments():
    return fetch_all("SELECT id, code, name, description, contact_email, contact_phone, color "
                     "FROM departments ORDER BY name")


@app.post("/api/analyze")
async def analyze(payload: dict):
    title = payload.get("title", "")
    description = payload.get("description", "")
    if not title.strip() and not description.strip():
        return {"ok": True, "department_id": None, "department_name": None,
                "confidence": 0.0, "method": "classifier", "matched_keywords": [], "explanation": ""}
    result = router.analyze(title, description)
    return {"ok": True, **result}


@app.post("/api/complaints")
async def submit_complaint(request: Request, payload: ComplaintIn):
    # Optional citizen session -> link the complaint to a registered user
    user_id = None
    sess = _auth(request)
    if sess and sess["role"] == "citizen":
        user_id = sess["user_id"]

    manual_code = (payload.manual_department_code or "").strip().upper()
    if manual_code:
        dept = fetch_one("SELECT * FROM departments WHERE UPPER(code) = ?", (manual_code,))
        if not dept:
            return JSONResponse({"ok": False, "message": f"Unknown department {manual_code}"}, 400)
        result = {
            "department_id": dept["id"], "department_code": dept["code"],
            "department_name": dept["name"], "confidence": 1.0, "method": "manual",
            "matched_keywords": [], "explanation": payload.manual_reason or "Manually selected by citizen.",
        }
    else:
        result = router.analyze(payload.title, payload.description)
        if result["department_id"] is None:
            return JSONResponse(
                {"ok": False,
                 "message": "We couldn't confidently route this complaint. "
                            "Add more detail, or choose the department manually below.",
                 "analysis": result}, 422)

    created = create_complaint(
        title=payload.title, description=payload.description, category=payload.category,
        location=payload.location, city=payload.city, pincode=payload.pincode,
        contact_name=payload.contact_name, contact_email=payload.contact_email,
        contact_phone=payload.contact_phone, department_id=result["department_id"],
        confidence=result["confidence"], method=result["method"],
        matched_keywords=result["matched_keywords"], user_id=user_id,
        note=result["explanation"],
    )
    log.info("New complaint %s -> dept %s (%s)", created["tracking_id"],
             result["department_code"], result["method"])
    return {"ok": True, **created, "department": result, "message":
            f"Complaint {created['tracking_id']} submitted. "
            f"{'Routed to' if result['method'] != 'manual' else 'Sent to'} {result['department_name']}."}


@app.get("/api/complaints/track")
async def track(tracking_id: str):
    complaint = get_complaint(tracking_id)
    if not complaint:
        return JSONResponse({"ok": False, "message": "No complaint found with that ID."}, 404)
    rating = fetch_one(
        "SELECT AVG(rating) AS avg, COUNT(*) AS n FROM feedback WHERE complaint_id = ?",
        (complaint["id"],),
    )
    return {"ok": True, "tracking_id": complaint["tracking_id"], "status": complaint["status"],
            "priority": complaint["priority"], "title": complaint["title"],
            "description": complaint["description"],
            "contact_name": complaint["contact_name"], "contact_email": complaint["contact_email"],
            "contact_phone": complaint["contact_phone"], "location": complaint["location"],
            "city": complaint["city"], "category": complaint["category"],
            "department": {"id": complaint["department_id"], "code": complaint["department_code"],
                           "name": complaint["department_name"], "color": complaint["department_color"]},
            "confidence": complaint["department_confidence"],
            "routing_method": complaint["routing_method"],
            "sla_due_at": complaint["sla_due_at"],
            "created_at": complaint["created_at"], "updated_at": complaint["updated_at"],
            "avg_rating": round(rating["avg"], 1) if rating and rating["n"] else None,
            "feedback_count": rating["n"] if rating else 0,
            "history": get_history(complaint["id"])}


# ---------------------------------------------------------------- citizen auth
@app.post("/api/auth/register")
async def register(payload: UserIn):
    return register_user(payload.full_name, payload.email, payload.phone,
                         payload.city, payload.password)


@app.post("/api/auth/login")
async def login_citizen(payload: UserLogin):
    result = login_user(payload.identifier, payload.password)
    if not result["ok"]:
        return JSONResponse(result, 401)
    return {"ok": True, "token": _new_session("citizen", user_id=result["user_id"]),
            "user": result}


@app.get("/api/auth/me")
async def me(request: Request):
    sess = _auth(request)
    if not sess:
        return JSONResponse({"ok": False, "message": "Not signed in"}, 401)
    user = fetch_one("SELECT id, full_name, email, phone, city, role FROM users WHERE id = ?",
                     (sess.get("user_id"),))
    if not user:
        return JSONResponse({"ok": False, "message": "User not found"}, 404)
    return {"ok": True, "user": user}


# ---------------------------------------------------------------- feedback
@app.post("/api/complaints/{complaint_id}/feedback")
async def feedback(request: Request, complaint_id: str, payload: FeedbackIn):
    user_id = None
    sess = _auth(request)
    if sess and sess["role"] == "citizen":
        user_id = sess["user_id"]
    return add_feedback(complaint_id, payload.rating, payload.comment, user_id)


# ---------------------------------------------------------------- department
@app.get("/api/dept/complaints")
async def dept_complaints(request: Request, status: str | None = None, priority: str | None = None):
    sess = _auth(request, allowed=["department", "admin"])
    if not sess:
        return JSONResponse({"ok": False, "message": "Not authorised"}, 401)
    # Department dashboard reads from its own queue (department_complaints table)
    rows = department_queue(sess["department_id"] if sess["role"] == "department"
                            else None, status) if sess["role"] == "department" else \
        list_complaints(None, status)
    if priority:
        rows = [r for r in rows if r["priority"] == priority.upper()]
    return {"ok": True, "complaints": rows}


@app.get("/api/dept/queue-stats")
async def dept_queue_stats(request: Request):
    sess = _auth(request, allowed=["department", "admin"])
    if not sess:
        return JSONResponse({"ok": False, "message": "Not authorised"}, 401)
    if sess["role"] != "department":
        return JSONResponse({"ok": False, "message": "Department only"}, 403)
    rows = fetch_all(
        """SELECT c.status, COUNT(*) AS total,
                  SUM(CASE WHEN c.status IN ('PENDING','IN_PROGRESS') THEN 1 ELSE 0 END) AS active,
                  SUM(CASE WHEN c.priority = 'URGENT' THEN 1 ELSE 0 END) AS urgent,
                  SUM(CASE WHEN dc.sla_due_at < ? AND c.status IN ('PENDING','IN_PROGRESS')
                           THEN 1 ELSE 0 END) AS overdue
           FROM department_complaints dc JOIN complaints c ON c.id = dc.complaint_id
           WHERE dc.department_id = ?
           GROUP BY c.status""",
        (now_utc(), sess["department_id"]),
    )
    return {"ok": True, "rows": rows}


@app.post("/api/dept/complaints/{complaint_id}/update")
async def dept_update(request: Request, complaint_id: str, payload: ComplaintUpdate):
    sess = _auth(request, allowed=["department", "admin"])
    if not sess:
        return JSONResponse({"ok": False, "message": "Not authorised"}, 401)
    complaint = get_complaint(complaint_id)
    if not complaint:
        return JSONResponse({"ok": False, "message": "Complaint not found"}, 404)
    if sess["role"] == "department" and complaint["department_id"] != sess["department_id"]:
        return JSONResponse({"ok": False, "message": "Not your department's complaint"}, 403)
    return update_complaint(complaint_id, status=payload.status, priority=payload.priority,
                            note=payload.note, changed_by="department",
                            reassign_code=payload.reassign_code if sess["role"] == "admin" else "")


# ---------------------------------------------------------------- admin
@app.get("/api/admin/overview")
async def admin_overview():
    return {"ok": True, **analytics.overview()}


@app.get("/api/admin/complaints")
async def admin_complaints(request: Request, status: str | None = None, limit: int = 500):
    _auth(request, allowed=["admin"])
    return {"ok": True, "complaints": list_complaints(None, status, limit)}


@app.post("/api/admin/complaints/{complaint_id}/update")
async def admin_update(request: Request, complaint_id: str, payload: ComplaintUpdate):
    sess = _auth(request, allowed=["admin"])
    if not sess:
        return JSONResponse({"ok": False, "message": "Not authorised"}, 401)
    return update_complaint(complaint_id, status=payload.status, priority=payload.priority,
                            note=payload.note, changed_by="admin",
                            reassign_code=payload.reassign_code)


@app.get("/api/admin/notifications")
async def admin_notifications(request: Request, limit: int = 100):
    _auth(request, allowed=["admin"])
    return {"ok": True, "notifications": fetch_all(
        "SELECT n.*, c.tracking_id FROM notifications n "
        "LEFT JOIN complaints c ON c.id = n.complaint_id "
        "ORDER BY n.created_at DESC LIMIT ?", (limit,))}


@app.get("/api/admin/llm-feedback")
async def admin_llm_feedback(request: Request):
    _auth(request, allowed=["admin"])
    return {"ok": True, "rows": fetch_all("SELECT * FROM llm_feedback ORDER BY created_at DESC LIMIT 100")}


@app.get("/api/admin/users")
async def admin_users(request: Request, limit: int = 500):
    _auth(request, allowed=["admin"])
    return {"ok": True, "users": list_users(limit)}


@app.get("/api/admin/feedback")
async def admin_feedback(request: Request, limit: int = 200):
    _auth(request, allowed=["admin"])
    return {"ok": True, "feedback": get_feedback(None, limit)}


@app.post("/api/admin/train")
async def admin_train(request: Request):
    _auth(request, allowed=["admin"])
    try:
        from app.routing.classifier import MLClassifier
        import train_model
        result = train_model.train_and_save()
        router.ml = MLClassifier()
        router.ml.build()
        return result
    except Exception as exc:
        return JSONResponse({"ok": False, "message": f"Training failed: {exc}"}, 500)


@app.post("/api/admin/complaints/{complaint_id}/manual-route")
async def admin_manual_route(request: Request, complaint_id: str, payload: dict):
    """Manually force a complaint to a department (overrides the auto-routing)."""
    sess = _auth(request, allowed=["admin"])
    if not sess:
        return JSONResponse({"ok": False, "message": "Not authorised"}, 401)
    code = (payload.get("department_code") or "").upper()
    note = payload.get("note", "")
    if not code:
        return JSONResponse({"ok": False, "message": "department_code required"}, 400)
    dept = fetch_one("SELECT id FROM departments WHERE UPPER(code) = ?", (code,))
    if not dept:
        return JSONResponse({"ok": False, "message": f"Unknown department {code}"}, 404)
    complaint = get_complaint(complaint_id)
    if not complaint:
        return JSONResponse({"ok": False, "message": "Complaint not found"}, 404)

    result = update_complaint(complaint_id, reassign_code=code,
                              note=f"Manually routed by admin. {note}".strip())
    ts = now_utc()
    from .database import db
    with db() as conn:
        conn.execute("UPDATE complaints SET routing_method = 'manual' WHERE id = ?", (complaint["id"],))
        conn.execute(
            "INSERT OR REPLACE INTO department_complaints"
            "(department_id, complaint_id, assigned_at, sla_due_at, queue_position) VALUES (?,?,?,?,?)",
            (dept["id"], complaint["id"], ts, complaint["sla_due_at"], 1))
    return result


# ---------------------------------------------------------------- analytics
@app.get("/api/analytics/overview")
async def api_overview():
    return {"ok": True, **analytics.overview()}


@app.get("/api/analytics/departments")
async def api_departments():
    return {"ok": True, "rows": analytics.by_department()}


@app.get("/api/analytics/status")
async def api_status():
    return {"ok": True, "rows": analytics.by_status()}


@app.get("/api/analytics/priority")
async def api_priority():
    return {"ok": True, "rows": analytics.by_priority()}


@app.get("/api/analytics/trend")
async def api_trend(days: int = 14):
    return {"ok": True, "rows": analytics.trend(days)}


@app.get("/api/analytics/routing")
async def api_routing():
    return {"ok": True, "rows": analytics.routing_methods()}


# ---------------------------------------------------------------- startup
@app.on_event("startup")
async def on_startup():
    init_db()
    seed()
    router.reload()
    log.info("ML classifier available: %s | LLM router enabled: %s",
             router.ml.available, router.llm.enabled)
    seed_demo_complaints()
    log.info("GrievancePath ready at / (citizen portal), /department, /admin, /analytics")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
