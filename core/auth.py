# core/auth.py
import hashlib
from core.db import get_connection


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def register_user(name: str, email: str, password: str, role: str = "ADMIN") -> bool:
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO users (name, email, password_hash, role)
            VALUES (?, ?, ?, ?)
            """,
            (name, email.lower().strip(), _hash_password(password), role),
        )
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


def login_user(email: str, password: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM users WHERE email = ?",
        (email.lower().strip(),),
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    if row["password_hash"] != _hash_password(password):
        return None
    return row


def is_admin(user) -> bool:
    if not user:
        return False
    return (user.get("role") or "").upper() == "ADMIN"
