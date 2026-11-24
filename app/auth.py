"""Passwordless email OTP authentication for TASKORA."""
import hashlib, hmac, os, re, secrets, smtplib, ssl
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from typing import Optional
from dotenv import load_dotenv
from fastapi import HTTPException, Request
from app.db import get_db_connection
load_dotenv()
OTP_TTL=timedelta(minutes=10); RESEND_SECONDS=60; MAX_ATTEMPTS=5; SESSION_TTL=timedelta(days=30)
EMAIL_RE=re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
def now(): return datetime.now(timezone.utc)
def stamp(value): return value.isoformat()
def init_auth_db():
    conn=get_db_connection()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT,email TEXT NOT NULL UNIQUE COLLATE NOCASE,display_name TEXT NOT NULL,role TEXT NOT NULL CHECK(role IN ('worker','employer')),email_verified INTEGER NOT NULL DEFAULT 1,created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS email_otps(email TEXT PRIMARY KEY COLLATE NOCASE,code_hash TEXT NOT NULL,display_name TEXT NOT NULL,role TEXT NOT NULL,expires_at TEXT NOT NULL,sent_at TEXT NOT NULL,attempts INTEGER NOT NULL DEFAULT 0);
    CREATE TABLE IF NOT EXISTS auth_sessions(token_hash TEXT PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,expires_at TEXT NOT NULL,created_at TEXT NOT NULL);
    """); conn.commit(); conn.close()
def otp_hash(email,code):
    secret=os.getenv("AUTH_SECRET","")
    if len(secret)<32: raise HTTPException(503,"Set AUTH_SECRET to a random value of at least 32 characters.")
    return hmac.new(secret.encode(),f"{email}:{code}".encode(),hashlib.sha256).hexdigest()
def send_email(email,code):
    host=os.getenv("SMTP_HOST"); username=os.getenv("SMTP_USERNAME"); password=os.getenv("SMTP_PASSWORD"); sender=os.getenv("SMTP_FROM") or username
    if not all((host,username,password,sender)): raise HTTPException(503,"Email OTP is not configured. Add SMTP settings to the deployment environment.")
    msg=EmailMessage(); msg["Subject"]="Your TASKORA verification code"; msg["From"]=sender; msg["To"]=email
    msg.set_content(f"Your TASKORA verification code is {code}. It expires in 10 minutes. Do not share it. If you did not request it, ignore this email.")
    with smtplib.SMTP(host,int(os.getenv("SMTP_PORT","587")),timeout=15) as smtp:
        if os.getenv("SMTP_USE_TLS","true").lower() in ("1","true","yes"): smtp.starttls(context=ssl.create_default_context())
        smtp.login(username,password); smtp.send_message(msg)
def request_otp(email,display_name,role):
    email=email.strip().lower(); display_name=display_name.strip()
    if not EMAIL_RE.fullmatch(email): raise HTTPException(422,"Enter a valid email address.")
    if role not in ("worker","employer"): raise HTTPException(422,"Choose worker or employer.")
    if not 2<=len(display_name)<=80: raise HTTPException(422,"Name must contain 2–80 characters.")
    conn=get_db_connection(); old=conn.execute("SELECT sent_at FROM email_otps WHERE email=?",(email,)).fetchone()
    if old:
        remaining=RESEND_SECONDS-(now()-datetime.fromisoformat(old["sent_at"])).total_seconds()
        if remaining>0: conn.close(); raise HTTPException(429,f"Wait {int(remaining)+1} seconds before requesting another code.")
    existing=conn.execute("SELECT role FROM users WHERE email=?",(email,)).fetchone()
    if existing and existing["role"]!=role: conn.close(); raise HTTPException(409,f"This email belongs to a {existing['role']} account.")
    code=f"{secrets.randbelow(1000000):06d}"; created=now()
    conn.execute("""INSERT INTO email_otps VALUES(?,?,?,?,?,?,0) ON CONFLICT(email) DO UPDATE SET code_hash=excluded.code_hash,display_name=excluded.display_name,role=excluded.role,expires_at=excluded.expires_at,sent_at=excluded.sent_at,attempts=0""",(email,otp_hash(email,code),display_name,role,stamp(created+OTP_TTL),stamp(created)))
    conn.commit(); conn.close()
    try: send_email(email,code)
    except Exception:
        conn=get_db_connection(); conn.execute("DELETE FROM email_otps WHERE email=?",(email,)); conn.commit(); conn.close(); raise
    return {"message":"Verification code sent. Check your inbox.","expires_in_seconds":600}
def verify_otp(email,code):
    email=email.strip().lower()
    if not re.fullmatch(r"\d{6}",code or ""): raise HTTPException(422,"Enter the 6-digit code.")
    conn=get_db_connection(); row=conn.execute("SELECT * FROM email_otps WHERE email=?",(email,)).fetchone()
    if not row: conn.close(); raise HTTPException(400,"Code is invalid or expired. Request a new one.")
    if datetime.fromisoformat(row["expires_at"])<=now():
        conn.execute("DELETE FROM email_otps WHERE email=?",(email,)); conn.commit(); conn.close(); raise HTTPException(400,"Code expired. Request a new one.")
    if row["attempts"]>=MAX_ATTEMPTS:
        conn.execute("DELETE FROM email_otps WHERE email=?",(email,)); conn.commit(); conn.close(); raise HTTPException(429,"Too many attempts. Request a new code.")
    if not hmac.compare_digest(row["code_hash"],otp_hash(email,code)):
        conn.execute("UPDATE email_otps SET attempts=attempts+1 WHERE email=?",(email,)); conn.commit(); conn.close(); raise HTTPException(400,"Incorrect code.")
    user=conn.execute("SELECT id FROM users WHERE email=?",(email,)).fetchone()
    if user: user_id=user["id"]
    else: user_id=conn.execute("INSERT INTO users(email,display_name,role,email_verified,created_at) VALUES(?,?,?,?,?)",(email,row["display_name"],row["role"],1,stamp(now()))).lastrowid
    token=secrets.token_urlsafe(32); conn.execute("INSERT INTO auth_sessions VALUES(?,?,?,?)",(hashlib.sha256(token.encode()).hexdigest(),user_id,stamp(now()+SESSION_TTL),stamp(now())))
    conn.execute("DELETE FROM email_otps WHERE email=?",(email,)); conn.commit()
    account=dict(conn.execute("SELECT id,email,display_name,role,email_verified FROM users WHERE id=?",(user_id,)).fetchone()); conn.close()
    return token,account
def current_user(request:Request)->Optional[dict]:
    token=request.cookies.get("taskora_session")
    if not token:
        auth=request.headers.get("Authorization","")
        if auth.lower().startswith("bearer "): token=auth[7:].strip()
    if not token: return None
    conn=get_db_connection(); row=conn.execute("""SELECT u.id,u.email,u.display_name,u.role,u.email_verified FROM auth_sessions s JOIN users u ON u.id=s.user_id WHERE s.token_hash=? AND s.expires_at>?""",(hashlib.sha256(token.encode()).hexdigest(),stamp(now()))).fetchone(); conn.close()
    return dict(row) if row else None
def require_role(role):
    def check(request:Request):
        user=current_user(request)
        if not user: raise HTTPException(401,"Sign in with a verified email first.")
        if user["role"]!=role: raise HTTPException(403,f"A {role} account is required.")
        return user
    return check
def logout(request:Request):
    token=request.cookies.get("taskora_session")
    if token:
        conn=get_db_connection(); conn.execute("DELETE FROM auth_sessions WHERE token_hash=?",(hashlib.sha256(token.encode()).hexdigest(),)); conn.commit(); conn.close()
