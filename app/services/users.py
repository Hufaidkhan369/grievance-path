"""Citizen user accounts stored in the users table."""
from __future__ import annotations

import hashlib
import secrets

from ..database import db, now_utc, fetch_all, fetch_one


def _hash(password: str, salt: str | None = None) -> tuple[str, str]:
    salt = salt or secrets.token_hex(8)
    digest = hashlib.sha256(f"{salt}:{password}".encode()).hexdigest()
    return f"{salt}${digest}", salt


def _verify(password: str, stored: str) -> bool:
    if not stored:
        return False
    salt, digest = stored.split("$", 1)
    check = hashlib.sha256(f"{salt}:{password}".encode()).hexdigest()
    return secrets.compare_digest(check, digest)


def register_user(full_name: str, email: str, phone: str, city: str, password: str) -> dict:
    email = (email or "").strip().lower()
    phone = (phone or "").strip()
    if not full_name.strip():
        return {"ok": False, "message": "Name is required."}
    if not email and not phone:
        return {"ok": False, "message": "Email or phone is required."}
    existing = fetch_one("SELECT id FROM users WHERE email = ? OR phone = ?", (email, phone))
    if existing:
        return {"ok": False, "message": "An account with that email/phone already exists."}

    pw_hash, _ = _hash(password or secrets.token_hex(6))
    ts = now_utc()
    with db() as conn:
        cur = conn.execute(
            "INSERT INTO users(full_name, email, phone, city, password_hash, role, created_at) "
            "VALUES (?,?,?,?,?,?,?)",
            (full_name.strip(), email or None, phone or None, city.strip(), pw_hash, "citizen", ts),
        )
        user_id = cur.lastrowid
    return {"ok": True, "user_id": user_id, "full_name": full_name.strip()}


def login_user(identifier: str, password: str) -> dict:
    identifier = (identifier or "").strip().lower()
    if not identifier:
        return {"ok": False, "message": "Enter your email or phone."}
    user = fetch_one("SELECT * FROM users WHERE email = ? OR phone = ?", (identifier, identifier))
    if not user:
        return {"ok": False, "message": "No account found with that email/phone."}
    if not _verify(password, user["password_hash"] or ""):
        return {"ok": False, "message": "Incorrect password."}
    return {"ok": True, "user_id": user["id"], "full_name": user["full_name"],
            "email": user["email"], "phone": user["phone"], "city": user["city"],
            "role": user["role"]}


def list_users(limit: int = 500) -> list[dict]:
    return fetch_all(
        """SELECT u.id, u.full_name, u.email, u.phone, u.city, u.role, u.created_at,
                  d.name AS department_name, COUNT(c.id) AS complaints
           FROM users u
           LEFT JOIN departments d ON d.id = u.department_id
           LEFT JOIN complaints c ON c.user_id = u.id
           GROUP BY u.id ORDER BY u.created_at DESC LIMIT ?""",
        (limit,),
    )
