"""
Unit tests for TASKORA Job Matching Algorithm (app/matcher.py)
Covers Haversine distance, ranking, filtering, pay weights, closed/reported jobs, and edge cases.
"""

from datetime import datetime, timezone, timedelta
import pytest
from app.matcher import (
    haversine_distance,
    calculate_recency_score,
    get_area_coordinates,
    match_jobs
)


def test_haversine_distance_calculation():
    """1. Test Haversine distance calculation against known coordinate pairs."""
    # Distance from Hebbal (13.0358, 77.5970) to Yelahanka (13.1007, 77.5963)
    # Expected distance is ~7.2 km
    dist = haversine_distance(13.0358, 77.5970, 13.1007, 77.5963)
    assert 7.0 <= dist <= 7.5

    # Same location distance must be 0
    assert haversine_distance(13.0358, 77.5970, 13.0358, 77.5970) == 0.0

    # Distance from Hebbal to Whitefield (~19-20 km)
    dist_wf = haversine_distance(13.0358, 77.5970, 12.9698, 77.7499)
    assert 18.0 <= dist_wf <= 22.0


def test_nearby_jobs_ranking():
    """2. Test that closer jobs rank higher when other parameters are identical."""
    now = datetime(2026, 11, 24, 12, 0, 0, tzinfo=timezone.utc)
    base_time = now.isoformat()

    # User in Hebbal (13.0358, 77.5970)
    jobs = [
        {
            "id": 1,
            "skill": "Electrician",
            "area": "Yelahanka",  # ~7.2 km away
            "latitude": 13.1007,
            "longitude": 77.5963,
            "pay": 800.0,
            "duration": "1 day",
            "employer_name": "Employer A",
            "employer_phone": "9000000001",
            "created_at": base_time,
            "status": "open",
            "report_count": 0
        },
        {
            "id": 2,
            "skill": "Electrician",
            "area": "Hebbal",  # 0 km away
            "latitude": 13.0358,
            "longitude": 77.5970,
            "pay": 800.0,
            "duration": "1 day",
            "employer_name": "Employer B",
            "employer_phone": "9000000002",
            "created_at": base_time,
            "status": "open",
            "report_count": 0
        }
    ]

    results = match_jobs("Electrician", "Hebbal", jobs, max_radius_km=10.0, now=now)
    assert len(results) == 2
    # The Hebbal job (0 km) should rank first with a higher final score
    assert results[0]["id"] == 2
    assert results[0]["distance"] == 0.0
    assert results[1]["id"] == 1
    assert results[0]["final_score"] > results[1]["final_score"]


def test_distance_filtering():
    """3. Test that jobs outside max_radius_km (default 10 km) are excluded."""
    now = datetime(2026, 11, 24, 12, 0, 0, tzinfo=timezone.utc)
    jobs = [
        {
            "id": 1,
            "skill": "Plumber",
            "area": "Hebbal",  # Reference is Hebbal
            "latitude": 13.0358,
            "longitude": 77.5970,
            "pay": 800.0,
            "status": "open",
            "report_count": 0,
            "created_at": now.isoformat()
        },
        {
            "id": 2,
            "skill": "Plumber",
            "area": "Whitefield",  # >18 km away from Hebbal
            "latitude": 12.9698,
            "longitude": 77.7499,
            "pay": 800.0,
            "status": "open",
            "report_count": 0,
            "created_at": now.isoformat()
        }
    ]

    results = match_jobs("Plumber", "Hebbal", jobs, max_radius_km=10.0, now=now)
    # Only Hebbal job should be included; Whitefield is beyond 10 km
    assert len(results) == 1
    assert results[0]["id"] == 1


def test_pay_based_ranking():
    """4. Test that higher pay provides a score boost among equidistant jobs."""
    now = datetime(2026, 11, 24, 12, 0, 0, tzinfo=timezone.utc)
    jobs = [
        {
            "id": 1,
            "skill": "Painter",
            "area": "Hebbal",
            "latitude": 13.0358,
            "longitude": 77.5970,
            "pay": 700.0,
            "status": "open",
            "report_count": 0,
            "created_at": now.isoformat()
        },
        {
            "id": 2,
            "skill": "Painter",
            "area": "Hebbal",
            "latitude": 13.0358,
            "longitude": 77.5970,
            "pay": 1000.0,  # Higher pay
            "status": "open",
            "report_count": 0,
            "created_at": now.isoformat()
        }
    ]

    results = match_jobs("Painter", "Hebbal", jobs, max_radius_km=10.0, now=now)
    assert len(results) == 2
    assert results[0]["id"] == 2
    assert results[0]["pay"] == 1000.0
    assert results[0]["score_breakdown"]["pay_fit_score"] == 1.0
    assert results[1]["score_breakdown"]["pay_fit_score"] == 0.7


def test_closed_jobs_exclusion():
    """5. Test that jobs with status != 'open' are excluded."""
    now = datetime(2026, 11, 24, 12, 0, 0, tzinfo=timezone.utc)
    jobs = [
        {
            "id": 1,
            "skill": "Mason",
            "area": "Hebbal",
            "latitude": 13.0358,
            "longitude": 77.5970,
            "pay": 800.0,
            "status": "closed",  # Closed job
            "report_count": 0,
            "created_at": now.isoformat()
        },
        {
            "id": 2,
            "skill": "Mason",
            "area": "Hebbal",
            "latitude": 13.0358,
            "longitude": 77.5970,
            "pay": 800.0,
            "status": "open",
            "report_count": 0,
            "created_at": now.isoformat()
        }
    ]

    results = match_jobs("Mason", "Hebbal", jobs, now=now)
    assert len(results) == 1
    assert results[0]["id"] == 2


def test_reported_jobs_exclusion():
    """6. Test that jobs with report_count >= 3 are excluded from matches."""
    now = datetime(2026, 11, 24, 12, 0, 0, tzinfo=timezone.utc)
    jobs = [
        {
            "id": 1,
            "skill": "Driver",
            "area": "Hebbal",
            "latitude": 13.0358,
            "longitude": 77.5970,
            "pay": 800.0,
            "status": "open",
            "report_count": 3,  # Reported 3 times
            "created_at": now.isoformat()
        },
        {
            "id": 2,
            "skill": "Driver",
            "area": "Hebbal",
            "latitude": 13.0358,
            "longitude": 77.5970,
            "pay": 800.0,
            "status": "open",
            "report_count": 2,  # Reported 2 times - still eligible
            "created_at": now.isoformat()
        }
    ]

    results = match_jobs("Driver", "Hebbal", jobs, now=now)
    assert len(results) == 1
    assert results[0]["id"] == 2


def test_missing_or_invalid_values():
    """7. Test robustness against missing, empty, or invalid candidate values."""
    jobs = [
        {
            "id": 1,
            "skill": "Cleaner",
            "area": "Hebbal",
            "latitude": 13.0358,
            "longitude": 77.5970,
            "pay": None,  # None pay
            "status": "open",
            "report_count": 0,
            "created_at": ""
        }
    ]

    # Non-existent candidate area
    assert match_jobs("Cleaner", "UnknownCity", jobs) == []

    # Empty candidate skill
    assert match_jobs("", "Hebbal", jobs) == []

    # Job with missing pay or created_at should not crash
    results = match_jobs("Cleaner", "Hebbal", jobs)
    assert len(results) == 1
    assert results[0]["score_breakdown"]["pay_fit_score"] == 0.0
    assert results[0]["score_breakdown"]["recency_score"] == 0.0
