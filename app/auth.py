"""Password-based signup, login, and sessions for TASKORA."""
import hashlib, hmac, re, secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import HTTPException, Request
from app.db import get_db_connection

SESSION_TTL = timedelta(days=30)
PASSWORD_ITERATIONS = 310_000
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

def now():
    return datetime.now(timezone.utc)

def stamp(value):
    return value.isoformat()

def init_auth_db():
    conn = get_db_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE COLLATE NOCASE,
            display_name TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('worker', 'employer')),
            email_verified INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            password_hash TEXT
        );
        CREATE TABLE IF NOT EXISTS auth_sessions (
            token_hash TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            expires_at TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_auth_sessions_user ON auth_sessions(user_id);
        DROP TABLE IF EXISTS email_otps;
    """)
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
    if "password_hash" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")
    conn.commit()
    conn.close()

def hash_password(password):
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PASSWORD_ITERATIONS)
    return f"pbkdf2_sha256${{PASSWORD_ITERATIONS}}${{salt.hex()}}${{digest.hex()}}"

def verify_password(password, stored):
    try:
        algorithm, iterations, salt_hex, digest_hex = stored.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), int(iterations))
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False

def validate_email(email):
    email = email.strip().lower()
    if len(email) > 254 or not EMAIL_RE.fullmatch(email):
        raise HTTPException(422, "Enter a valid email address.")
    return email

def validate_password(password):
    if len(password) < 8:
        raise HTTPException(422, "Password must be at least 8 characters long.")
    if len(password) > 128:
        raise HTTPException(422, "Password must be 128 characters or fewer.")

def create_session(conn, user_id):
    token = secrets.token_urlsafe(32)
    conn.execute(
        "INSERT INTO auth_sessions VALUES (?, ?, ?, ?)",
        (hashlib.sha256(token.encode()).hexdigest(), user_id,
         stamp(now() + SESSION_TTL), stamp(now()))
    )
    return token

def public_user(conn, user_id):
    return dict(conn.execute(
        "SELECT id, email, display_name, role FROM users WHERE id = ?", (user_id,)
    ).fetchone())

def signup(email, password, display_name, role):
    email = validate_email(email)
    validate_password(password)
    display_name = display_name.strip()
    if not 2 <= len(display_name) <= 80:
        raise HTTPException(422, "Name must contain 2–80 characters.")
    if role not in ("worker", "employer"):
        raise HTTPException(422, "Choose worker or employer.")
    conn = get_db_connection()
    existing = conn.execute("SELECT id, password_hash FROM users WHERE email = ?", (email,)).fetchone()
    encoded = hash_password(password)
    if existing and existing["password_hash"]:
        conn.close()
        raise HTTPException(409, "An account with this email already exists. Please log in.")
    if existing:
        # Allow legacy OTP-era rows to set a password; email verification is intentionally disabled.
        conn.execute("UPDATE users SET password_hash=?, display_name=?, role=?, email_verified=0 WHERE id=?",
                     (encoded, display_name, role, existing["id"]))
        user_id = existing["id"]
    else:
        user_id = conn.execute(
            "INSERT INTO users(email,display_name,role,email_verified,created_at,password_hash) VALUES(?,?,?,0,?,?)",
            (email, display_name, role, stamp(now()), encoded)
        ).lastrowid
    token = create_session(conn, user_id)
    conn.commit()
    account = public_user(conn, user_id)
    conn.close()
    return token, account

def login(email, password):
    email = validate_email(email)
    if not password or len(password) > 128:
        raise HTTPException(401, "Invalid email or password.")
    conn = get_db_connection()
    row = conn.execute("SELECT id, password_hash FROM users WHERE email = ?", (email,)).fetchone()
    if not row or not row["password_hash"] or not verify_password(password, row["password_hash"]):
        conn.close()
        raise HTTPException(401, "Invalid email or password.")
    token = create_session(conn, row["id"])
    account = public_user(conn, row["id"])
    conn.commit()
    conn.close()
    return token, account

def current_user(request: Request) -> Optional[dict]:
    token = request.cookies.get("taskora_session")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.lower().startswith("bearer "):
            token = auth[7:].strip()
    if not token:
        return None
    conn = get_db_connection()
    row = conn.execute(
        """SELECT u.id,u.email,u.display_name,u.role FROM auth_sessions s
           JOIN users u ON u.id=s.user_id WHERE s.token_hash=? AND s.expires_at>?""",
        (hashlib.sha256(token.encode()).hexdigest(), stamp(now()))
    ).fetchone()
    conn.close()
    return dict(row) if row else None

def require_role(role):
    def check(request: Request):
        user = current_user(request)
        if not user:
            raise HTTPException(401, "Please log in to continue.")
        if user["role"] != role:
            raise HTTPException(403, f"A {role} account is required.")
        return user
    return check

def logout(request: Request):
    token = request.cookies.get("taskora_session")
    if token:
        conn = get_db_connection()
        conn.execute("DELETE FROM auth_sessions WHERE token_hash=?",
                     (hashlib.sha256(token.encode()).hexdigest(),))
        conn.commit()
        conn.close()
