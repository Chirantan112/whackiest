"""
Integration tests for TASKORA frontend pages (index.html, worker.html, employer.html).
Verifies HTML responses, status codes, branding, disclaimers, and interactive controls.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_landing_page():
    """Verify landing page loads with 200 OK and contains key branding."""
    response = client.get("/")
    assert response.status_code == 200
    html = response.text
    assert "TASKORA" in html
    assert "Say your skill. Find work nearby." in html
    assert "I Need Work" in html
    assert "I Need a Worker" in html
    assert "Demo data. Employer verification is not implemented yet." in html


def test_worker_page():
    """Verify worker page loads with 200 OK and contains microphone and search controls."""
    response = client.get("/worker")
    assert response.status_code == 200
    html = response.text
    assert "TASKORA" in html
    assert "micBtn" in html
    assert 'data-lang="kn"' in html
    assert "getSpeechLocale(TASKORA.state.language)" in html
    assert "transcriptInput" in html
    assert "searchBtn" in html
    assert "jobsList" in html
    assert "Demo data. Employer verification is not implemented yet." in html


def test_employer_page():
    """Verify employer page loads with 200 OK and contains posting form and inputs."""
    response = client.get("/employer")
    assert response.status_code == 200
    html = response.text
    assert "TASKORA" in html
    assert "empMicBtn" in html
    assert 'data-lang="kn"' in html
    assert "getSpeechLocale(TASKORA.state.language)" in html
    assert "empTranscript" in html
    assert "jobPostForm" in html
    assert "formSkill" in html
    assert "formArea" in html
    assert "Demo data. Employer verification is not implemented yet." in html


def test_static_assets():
    """Verify static CSS and JS are served properly."""
    css_resp = client.get("/static/style.css")
    assert css_resp.status_code == 200
    assert "--primary" in css_resp.text

    js_resp = client.get("/static/app.js")
    assert js_resp.status_code == 200
    assert "TASKORA" in js_resp.text
    assert "kn-IN" in js_resp.text
    assert "state.recognition = recognition" in js_resp.text
