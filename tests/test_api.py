"""
Unit and integration tests for TASKORA FastAPI Endpoints (app/main.py)
Tests parse, search, create job, report job, health, and TTS fallback.
"""

import hashlib
import secrets
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db import init_db, get_db_connection
from app.auth import init_auth_db, now, stamp, SESSION_TTL

# Initialize database before tests run
init_db()
init_auth_db()
client = TestClient(app)


def get_employer_headers():
    """Generates a valid session token for a verified employer test account."""
    conn = get_db_connection()
    user = conn.execute("SELECT id FROM users WHERE email=?", ("test_employer@example.com",)).fetchone()
    if not user:
        user_id = conn.execute(
            "INSERT INTO users(email, display_name, role, email_verified, created_at) VALUES (?, ?, ?, ?, ?)",
            ("test_employer@example.com", "Test Employer", "employer", 1, stamp(now()))
        ).lastrowid
    else:
        user_id = user["id"]

    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    conn.execute(
        "INSERT INTO auth_sessions VALUES (?, ?, ?, ?)",
        (token_hash, user_id, stamp(now() + SESSION_TTL), stamp(now()))
    )
    conn.commit()
    conn.close()
    return {"Authorization": f"Bearer {token}"}


def test_health_check():
    """Verify health endpoint returns open jobs count and demo disclaimer."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["app"] == "TASKORA"
    assert data["open_jobs_count"] >= 20
    assert "disclaimer" in data


def test_areas_endpoint():
    """Verify areas endpoint returns 12 Bengaluru areas."""
    response = client.get("/api/areas")
    assert response.status_code == 200
    data = response.json()
    assert "areas" in data
    assert len(data["areas"]) == 12


def test_parse_endpoint():
    """Verify POST /api/parse extracts skill, area, pay, and duration from natural language."""
    payload = {
        "text": "I am looking for an electrician in Hebbal for 2 days offering 900 rupees per day"
    }
    response = client.post("/api/parse", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["skill"] == "Electrician"
    assert data["area"] == "Hebbal"
    assert data["pay"] == 900.0
    assert data["duration"] == "2 days"
    assert data["is_complete"] is True
    assert len(data["missing_fields"]) == 0


def test_parse_missing_fields():
    """Verify POST /api/parse detects missing fields and gives a follow-up prompt."""
    payload = {"text": "I need help in Whitefield"}
    response = client.post("/api/parse", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["skill"] is None
    assert data["area"] == "Whitefield"
    assert "skill" in data["missing_fields"]
    assert data["is_complete"] is False
    assert data["follow_up_question"] is not None


def test_search_jobs_endpoint():
    """Verify GET /api/jobs/search returns ranked matching jobs."""
    response = client.get("/api/jobs/search?skill=Electrician&area=Hebbal&max_radius_km=15")
    assert response.status_code == 200
    data = response.json()
    assert "jobs" in data
    assert len(data["jobs"]) > 0
    first_job = data["jobs"][0]
    assert first_job["skill"] == "Electrician"
    assert "distance" in first_job
    assert "final_score" in first_job
    assert "score_breakdown" in first_job


def test_create_job_endpoint():
    """Verify POST /api/jobs enforces employer auth, creates listing, and assigns coordinates."""
    payload = {
        "skill": "Plumber",
        "area": "Koramangala",
        "description": "Urgent kitchen sink repair",
        "pay": 850.0,
        "duration": "1 day",
        "employer_name": "Test Employer",
        "employer_phone": "9000000099"
    }

    # Without auth: should return 401 Unauthorized
    unauth_resp = client.post("/api/jobs", json=payload)
    assert unauth_resp.status_code == 401

    # With employer auth: should create job and return 201 Created
    headers = get_employer_headers()
    response = client.post("/api/jobs", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert "job" in data
    job = data["job"]
    assert job["skill"] == "Plumber"
    assert job["area"] == "Koramangala"
    assert job["latitude"] is not None
    assert job["longitude"] is not None
    assert job["pay"] == 850.0


def test_report_job_endpoint():
    """Verify POST /api/jobs/{id}/report increments report count."""
    headers = get_employer_headers()
    # Create a dummy job first
    payload = {
        "skill": "Painter",
        "area": "Hebbal",
        "description": "Temporary job to report",
        "pay": 700.0,
        "duration": "1 day",
        "employer_name": "Report Target",
        "employer_phone": "9000000088"
    }
    create_resp = client.post("/api/jobs", json=payload, headers=headers)
    assert create_resp.status_code == 201
    job_id = create_resp.json()["job"]["id"]

    # Report once
    rep1 = client.post(f"/api/jobs/{job_id}/report")
    assert rep1.status_code == 200
    assert rep1.json()["report_count"] == 1

    # Report second time
    rep2 = client.post(f"/api/jobs/{job_id}/report")
    assert rep2.json()["report_count"] == 2

    # Report third time -> status should become flagged
    rep3 = client.post(f"/api/jobs/{job_id}/report")
    assert rep3.json()["report_count"] == 3
    assert rep3.json()["status"] == "flagged"


def test_auth_me_endpoint():
    """Verify GET /api/auth/me returns 401 when unauthenticated and user data when authenticated."""
    # Unauthenticated -> 401 Not signed in
    unauth = client.get("/api/auth/me")
    assert unauth.status_code == 401

    # Authenticated -> 200 with user profile
    headers = get_employer_headers()
    auth_resp = client.get("/api/auth/me", headers=headers)
    assert auth_resp.status_code == 200
    assert auth_resp.json()["user"] is not None
    assert auth_resp.json()["user"]["role"] == "employer"


def test_tts_fallback_endpoint():
    """Verify POST /api/tts returns fallback=True when ElevenLabs API key is absent."""
    payload = {
        "text": "Hello, here are your matching jobs",
        "language": "en"
    }
    response = client.post("/api/tts", json=payload)
    assert response.status_code == 200
    data = response.json()
    # In test environment without valid ELEVENLABS_API_KEY, fallback must be True
    assert data["fallback"] is True
    assert data["audio_url"] is None
