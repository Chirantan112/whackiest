"""
TASKORA - Database Layer (SQLite)
Handles database connection, table initialization, parameterized queries, and seed data.
Beginner-friendly and purely using Python's built-in sqlite3.
"""

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Base directory paths
BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = BASE_DIR / "data" / "taskora.db"
SEED_JOBS_PATH = BASE_DIR / "data" / "seed_jobs.json"
AREAS_PATH = BASE_DIR / "data" / "areas.json"


def get_db_connection(db_path: Optional[str | Path] = None) -> sqlite3.Connection:
    """
    Creates and returns a connection to the SQLite database.
    Row factory is set to sqlite3.Row for dictionary-like column access.
    """
    target_path = Path(db_path) if db_path else DEFAULT_DB_PATH
    target_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target_path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[str | Path] = None, seed_if_empty: bool = True) -> None:
    """
    Creates the jobs table if it does not exist and populates seed data
    only if the table is currently empty.
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    # Create the jobs table with parameterized structure
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            skill TEXT NOT NULL,
            description TEXT,
            area TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            pay REAL,
            duration TEXT,
            employer_name TEXT NOT NULL,
            employer_phone TEXT NOT NULL,
            created_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            report_count INTEGER NOT NULL DEFAULT 0
        )
    """)
    conn.commit()

    if seed_if_empty:
        cursor.execute("SELECT COUNT(*) FROM jobs")
        count = cursor.fetchone()[0]
        if count == 0 and SEED_JOBS_PATH.exists():
            with open(SEED_JOBS_PATH, "r", encoding="utf-8") as f:
                seed_data = json.load(f)

            for job in seed_data:
                cursor.execute("""
                    INSERT INTO jobs (
                        skill, description, area, latitude, longitude,
                        pay, duration, employer_name, employer_phone,
                        created_at, status, report_count
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    job.get("skill", ""),
                    job.get("description", ""),
                    job.get("area", ""),
                    float(job.get("latitude", 0.0)),
                    float(job.get("longitude", 0.0)),
                    float(job.get("pay", 0.0)) if job.get("pay") is not None else None,
                    job.get("duration", ""),
                    job.get("employer_name", "Anonymous Employer"),
                    job.get("employer_phone", "9000000000"),
                    job.get("created_at", datetime.now(timezone.utc).isoformat()),
                    job.get("status", "open"),
                    int(job.get("report_count", 0))
                ))
            conn.commit()

    conn.close()


def get_open_jobs(db_path: Optional[str | Path] = None) -> List[Dict[str, Any]]:
    """
    Retrieves all open jobs with fewer than 3 reports.
    Uses parameterized query.
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM jobs
        WHERE status = 'open' AND report_count < 3
        ORDER BY created_at DESC
    """)
    rows = cursor.fetchall()
    jobs = [dict(row) for row in rows]
    conn.close()
    return jobs


def get_job_by_id(job_id: int, db_path: Optional[str | Path] = None) -> Optional[Dict[str, Any]]:
    """
    Retrieves a single job by its ID.
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def insert_job(job_data: Dict[str, Any], db_path: Optional[str | Path] = None) -> int:
    """
    Inserts a newly posted job and returns the generated job ID.
    All parameters are strictly parameterized to prevent SQL injection.
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    created_at = job_data.get("created_at") or datetime.now(timezone.utc).isoformat()
    status = job_data.get("status", "open")
    report_count = int(job_data.get("report_count", 0))

    cursor.execute("""
        INSERT INTO jobs (
            skill, description, area, latitude, longitude,
            pay, duration, employer_name, employer_phone,
            created_at, status, report_count
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        job_data["skill"].strip(),
        job_data.get("description", "").strip(),
        job_data["area"].strip(),
        float(job_data["latitude"]),
        float(job_data["longitude"]),
        float(job_data["pay"]) if job_data.get("pay") is not None else None,
        job_data.get("duration", "").strip(),
        job_data.get("employer_name", "Anonymous Employer").strip(),
        job_data.get("employer_phone", "").strip(),
        created_at,
        status,
        report_count
    ))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id


def report_job(job_id: int, db_path: Optional[str | Path] = None) -> Optional[Dict[str, Any]]:
    """
    Increments the report count for a job.
    If report_count reaches 3, the job status is set to 'flagged'.
    Returns the updated job dict or None if not found.
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, report_count FROM jobs WHERE id = ?", (job_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None

    new_count = row["report_count"] + 1
    new_status = "flagged" if new_count >= 3 else "open"

    cursor.execute("""
        UPDATE jobs
        SET report_count = ?, status = CASE WHEN ? >= 3 THEN 'flagged' ELSE status END
        WHERE id = ?
    """, (new_count, new_count, job_id))
    conn.commit()

    cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
    updated_row = cursor.fetchone()
    conn.close()
    return dict(updated_row) if updated_row else None


def load_areas(areas_path: Optional[str | Path] = None) -> List[Dict[str, Any]]:
    """
    Loads supported localities and their coordinates from areas.json.
    """
    path = Path(areas_path) if areas_path else AREAS_PATH
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("areas", [])
