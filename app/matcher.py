"""
TASKORA - Hyper-Local Job Matching Algorithm
Implements Haversine distance calculation and multi-factor weighted scoring.
Transparent, deterministic, and beginner-friendly for hackathon presentation and viva defense.
"""

import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from app.db import load_areas

# Earth radius in kilometers for Haversine calculation
EARTH_RADIUS_KM = 6371.0


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculates the great-circle distance between two GPS coordinates in kilometers
    using the Haversine formula.
    """
    # Convert degrees to radians
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    # Haversine central angle calculation
    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2))
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))

    return EARTH_RADIUS_KM * c


def get_area_coordinates(area_name: str, areas_list: Optional[List[Dict[str, Any]]] = None) -> Optional[Tuple[float, float]]:
    """
    Looks up the approximate center latitude and longitude for a given locality.
    """
    areas = areas_list if areas_list is not None else load_areas()
    target = area_name.strip().lower()

    for item in areas:
        name = item.get("name", "").lower()
        aliases = [a.lower() for a in item.get("aliases", [])]
        if target == name or target in aliases:
            return (float(item["latitude"]), float(item["longitude"]))

    return None


def calculate_recency_score(created_at_str: str, now: Optional[datetime] = None) -> float:
    """
    Calculates recency score:
    1.0 for jobs posted today, decaying linearly to 0.0 over 7 days.
    Never allows negative scores.
    """
    if not created_at_str:
        return 0.0

    current_time = now if now is not None else datetime.now(timezone.utc)

    # Parse ISO timestamp
    clean_str = created_at_str.replace("Z", "+00:00")
    try:
        created_time = datetime.fromisoformat(clean_str)
        if created_time.tzinfo is None:
            created_time = created_time.replace(tzinfo=timezone.utc)
        else:
            created_time = created_time.astimezone(timezone.utc)
    except Exception:
        return 0.0

    age_seconds = (current_time - created_time).total_seconds()
    age_days = max(0.0, age_seconds / 86400.0)

    # Linear decay over 7 days: 1 - (age_days / 7.0)
    score = 1.0 - (age_days / 7.0)
    return max(0.0, min(1.0, score))


def match_jobs(
    candidate_skill: str,
    candidate_area: str,
    all_jobs: List[Dict[str, Any]],
    max_radius_km: float = 10.0,
    top_n: int = 5,
    custom_coords: Optional[Tuple[float, float]] = None,
    now: Optional[datetime] = None
) -> List[Dict[str, Any]]:
    """
    Matches open jobs for a worker based on skill, distance, recency, and pay.

    Scoring formula:
    Final Score = (0.5 * Skill Match) + (0.3 * Distance Score) + (0.1 * Recency Score) + (0.1 * Pay Fit Score)

    Rules:
    - Only shows open jobs.
    - Hides jobs with report_count >= 3.
    - Matches exact normalized skill.
    - Limits to max_radius_km (default: 10 km).
    - Returns top 5 ranked jobs.
    """
    if not candidate_skill:
        return []

    norm_skill = candidate_skill.strip().lower()

    # Determine reference coordinates for distance calculation
    if custom_coords:
        ref_lat, ref_lon = custom_coords
    else:
        coords = get_area_coordinates(candidate_area)
        if not coords:
            return []
        ref_lat, ref_lon = coords

    # 1. Filter eligible jobs
    eligible = []
    for job in all_jobs:
        # Check open status
        if job.get("status", "").lower() != "open":
            continue

        # Exclude reported jobs (3 or more reports)
        if int(job.get("report_count", 0)) >= 3:
            continue

        # Skill match check
        job_skill = str(job.get("skill", "")).strip().lower()
        if job_skill != norm_skill:
            continue

        job_lat = float(job.get("latitude", 0.0))
        job_lon = float(job.get("longitude", 0.0))

        dist_km = haversine_distance(ref_lat, ref_lon, job_lat, job_lon)

        # Distance filter
        if dist_km > max_radius_km:
            continue

        eligible.append((job, dist_km))

    if not eligible:
        return []

    # 2. Determine max pay among eligible jobs for relative normalization
    max_pay = 0.0
    for job, _ in eligible:
        pay = float(job.get("pay") or 0.0)
        if pay > max_pay:
            max_pay = pay

    # 3. Score each eligible job
    scored_jobs = []
    for job, dist_km in eligible:
        # Skill Match: 1.0 (since already filtered by skill)
        skill_score = 1.0

        # Distance Score: 1 - (dist / max_radius)
        distance_score = max(0.0, min(1.0, 1.0 - (dist_km / max_radius_km)))

        # Recency Score
        recency_score = calculate_recency_score(job.get("created_at", ""), now=now)

        # Pay Fit Score
        job_pay = float(job.get("pay") or 0.0)
        pay_fit_score = (job_pay / max_pay) if max_pay > 0 else 0.0

        # Final Weighted Formula
        final_score = (
            0.5 * skill_score +
            0.3 * distance_score +
            0.1 * recency_score +
            0.1 * pay_fit_score
        )

        scored_jobs.append({
            "id": job.get("id"),
            "skill": job.get("skill"),
            "description": job.get("description"),
            "area": job.get("area"),
            "distance": round(dist_km, 1),
            "pay": job.get("pay"),
            "duration": job.get("duration"),
            "employer_name": job.get("employer_name"),
            "employer_phone": job.get("employer_phone"),
            "created_at": job.get("created_at"),
            "status": job.get("status"),
            "report_count": job.get("report_count", 0),
            "final_score": round(final_score, 3),
            "score_breakdown": {
                "skill_score": round(skill_score, 2),
                "distance_score": round(distance_score, 2),
                "recency_score": round(recency_score, 2),
                "pay_fit_score": round(pay_fit_score, 2)
            }
        })

    # Sort descending by final score
    scored_jobs.sort(key=lambda x: x["final_score"], reverse=True)

    # Return top N (default 5)
    return scored_jobs[:top_n]
