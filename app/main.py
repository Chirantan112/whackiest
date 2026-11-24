"""
TASKORA - FastAPI Main Application
Hyper-Local Job Matching for Informal & Semi-Skilled Workers.
Provides RESTful APIs for natural-language parsing, job matching, job posting, reporting, and voice TTS.
Serves the HTML/CSS/JS frontend directly for a unified, production-ready developer experience.
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.db import (
    init_db,
    get_open_jobs,
    get_job_by_id,
    insert_job,
    report_job,
    load_areas
)
from app.extract import extract_job_details, SKILL_DICTIONARY
from app.matcher import match_jobs, get_area_coordinates
from app.voice import generate_speech

BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = BASE_DIR / "web"
WEB_DIR.mkdir(parents=True, exist_ok=True)
AUDIO_CACHE_DIR = BASE_DIR / "audio_cache"
AUDIO_CACHE_DIR.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Initializes database and loads seed jobs on startup if empty.
    """
    init_db()
    yield


app = FastAPI(
    title="TASKORA API",
    description="Voice-first hyper-local job matching platform for informal & semi-skilled workers.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for development flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount audio cache directory for generated MP3 files
app.mount("/audio_cache", StaticFiles(directory=str(AUDIO_CACHE_DIR)), name="audio_cache")

# Mount web directory for static CSS/JS
app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")


# ---------------------------------------------------------------------------
# Request & Response Models (Pydantic)
# ---------------------------------------------------------------------------

class ParseRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Natural-language worker or employer statement.")


class CreateJobRequest(BaseModel):
    skill: str = Field(..., min_length=2, description="Normalized skill name (e.g. Electrician).")
    area: str = Field(..., min_length=2, description="Bengaluru locality (e.g. Hebbal).")
    description: Optional[str] = Field(None, description="Detailed job description.")
    pay: Optional[float] = Field(None, ge=0, description="Pay in rupees (e.g. 800).")
    duration: Optional[str] = Field(None, description="Job duration (e.g. 3 days).")
    employer_name: str = Field(..., min_length=2, description="Name of employer or business.")
    employer_phone: str = Field(..., min_length=7, description="Contact phone number.")
    latitude: Optional[float] = Field(None, description="Optional latitude.")
    longitude: Optional[float] = Field(None, description="Optional longitude.")


class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Text to synthesize into speech.")
    language: Optional[str] = Field("en", description="Language code ('en', 'hi', or 'kn').")


# ---------------------------------------------------------------------------
# Frontend Page Routes
# ---------------------------------------------------------------------------

@app.get("/", response_class=FileResponse, tags=["Frontend"])
async def read_landing():
    index_path = WEB_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Landing page not found")
    return FileResponse(index_path)


@app.get("/worker", response_class=FileResponse, tags=["Frontend"])
async def read_worker_page():
    page_path = WEB_DIR / "worker.html"
    if not page_path.exists():
        raise HTTPException(status_code=404, detail="Worker page not found")
    return FileResponse(page_path)


@app.get("/employer", response_class=FileResponse, tags=["Frontend"])
async def read_employer_page():
    page_path = WEB_DIR / "employer.html"
    if not page_path.exists():
        raise HTTPException(status_code=404, detail="Employer page not found")
    return FileResponse(page_path)


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/health", tags=["System"])
async def health_check():
    """Returns system status and database health check."""
    jobs = get_open_jobs()
    return {
        "status": "healthy",
        "app": "TASKORA",
        "open_jobs_count": len(jobs),
        "disclaimer": "Demo data. Employer verification is not implemented yet."
    }


@app.get("/api/areas", tags=["Metadata"])
async def get_areas():
    """Returns list of supported Bengaluru localities and center coordinates."""
    areas = load_areas()
    return {"areas": areas}


@app.get("/api/skills", tags=["Metadata"])
async def get_skills():
    """Returns supported skills and sample multilingual keywords."""
    return {
        "skills": list(SKILL_DICTIONARY.keys()),
        "dictionary": SKILL_DICTIONARY
    }


@app.post("/api/parse", tags=["Parsing"])
async def parse_natural_language(req: ParseRequest):
    """
    Accepts natural-language input from worker or employer voice transcript.
    Extracts skill, area, pay amount, duration, and flags missing fields.
    """
    result = extract_job_details(req.text)
    return result


@app.get("/api/jobs/search", tags=["Matching"])
async def search_matching_jobs(
    skill: str = Query(..., description="Worker's skill (e.g. Electrician)"),
    area: str = Query(..., description="Worker's locality in Bengaluru (e.g. Hebbal)"),
    max_radius_km: float = Query(10.0, ge=1.0, le=50.0, description="Search radius in kilometers")
):
    """
    Finds nearby matching jobs based on skill and geographic distance.
    Returns the top 5 matching open jobs ranked by weighted scoring.
    """
    if not skill or not area:
        raise HTTPException(status_code=400, detail="Both 'skill' and 'area' query parameters are required.")

    # Fetch open jobs from database
    all_jobs = get_open_jobs()

    # Run matching algorithm
    matches = match_jobs(
        candidate_skill=skill,
        candidate_area=area,
        all_jobs=all_jobs,
        max_radius_km=max_radius_km,
        top_n=5
    )

    return {
        "query": {
            "skill": skill,
            "area": area,
            "max_radius_km": max_radius_km
        },
        "total_matches": len(matches),
        "jobs": matches
    }


@app.post("/api/jobs", status_code=status.HTTP_201_CREATED, tags=["Jobs"])
async def create_job(req: CreateJobRequest):
    """
    Creates a new job listing posted by an employer.
    Validates required fields and automatically assigns approximate coordinates
    from the selected locality if not explicitly provided.
    """
    # Verify locality and lookup coordinates
    lat = req.latitude
    lon = req.longitude
    if lat is None or lon is None:
        coords = get_area_coordinates(req.area)
        if not coords:
            raise HTTPException(
                status_code=400,
                detail=f"Area '{req.area}' is not a recognized Bengaluru locality."
            )
        lat, lon = coords

    job_data = {
        "skill": req.skill,
        "description": req.description or f"{req.skill} required in {req.area}",
        "area": req.area,
        "latitude": lat,
        "longitude": lon,
        "pay": req.pay,
        "duration": req.duration or "1 day",
        "employer_name": req.employer_name,
        "employer_phone": req.employer_phone,
        "status": "open",
        "report_count": 0
    }

    new_id = insert_job(job_data)
    created_job = get_job_by_id(new_id)

    return {
        "message": "Job posted successfully",
        "job": created_job
    }


@app.post("/api/jobs/{job_id}/report", tags=["Jobs"])
async def report_suspicious_job(job_id: int):
    """
    Increments report count for a job. Automatically flags and hides
    jobs that receive 3 or more reports.
    """
    updated_job = report_job(job_id)
    if not updated_job:
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "message": "Job reported successfully",
        "job_id": job_id,
        "report_count": updated_job["report_count"],
        "status": updated_job["status"]
    }


@app.post("/api/tts", tags=["Voice"])
async def text_to_speech(req: TTSRequest):
    """
    Generates audio speech using ElevenLabs API when configured.
    Falls back gracefully with fallback=True if API key is not present.
    """
    result = generate_speech(req.text, language=req.language or "en")
    return result
