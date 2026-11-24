"""
Unit tests for TASKORA Natural Language Extraction Module (app/extract.py)
Covers English, Hindi, Romanized Hindi, area, pay, duration, and missing fields handling.
"""

import pytest
from app.extract import (
    extract_skill,
    extract_area,
    extract_pay,
    extract_duration,
    extract_job_details
)


def test_english_skill_extraction():
    """1. Test extraction of skills expressed in standard English."""
    assert extract_skill("I am looking for an electrician near Hebbal") == "Electrician"
    assert extract_skill("Need a skilled plumber for pipe leakage") == "Plumber"
    assert extract_skill("We require a carpenter for wooden cupboards") == "Carpenter"
    assert extract_skill("Need a painter for house painting") == "Painter"
    assert extract_skill("Looking for a security guard for night shift") == "Security Guard"


def test_hindi_skill_extraction():
    """2. Test extraction of skills expressed in Devanagari Hindi."""
    assert extract_skill("मुझे बिजली मिस्त्री की जरूरत है") == "Electrician"
    assert extract_skill("घर के लिए नल मिस्त्री चाहिए") == "Plumber"
    assert extract_skill("दीवार के लिए पेंटर की आवश्यकता है") == "Painter"
    assert extract_skill("अलमारी बनाने के लिए बढ़ई चाहिए") == "Carpenter"
    assert extract_skill("दीवार बनाने के लिए राज मिस्त्री") == "Mason"
    assert extract_skill("खाना बनाने वाला चाहिए") == "Cook"


def test_romanized_hindi_skill_extraction():
    """3. Test extraction of skills expressed in Romanized Hindi."""
    assert extract_skill("mujhe bijli wala chahiye urgent") == "Electrician"
    assert extract_skill("nal wala bula do") == "Plumber"
    assert extract_skill("rang wala kaam karega") == "Painter"
    assert extract_skill("badhai ko bulao") == "Carpenter"
    assert extract_skill("raj mistri available hai kya") == "Mason"
    assert extract_skill("rasoiya chahiye lunch banane ke liye") == "Cook"
    assert extract_skill("safai wala chahiye ghar ke liye") == "Cleaner"
    assert extract_skill("chowkidar chahiye layout ke liye") == "Security Guard"


def test_area_extraction():
    """4. Test extraction of Bengaluru areas and aliases."""
    assert extract_area("I live in Hebbal near flyover") == "Hebbal"
    assert extract_area("Looking for work in Koramangala 4th block") == "Koramangala"
    assert extract_area("Urgent requirement in Whitefield ITPL") == "Whitefield"
    assert extract_area("Office in ECity phase 1") == "Electronic City"
    assert extract_area("Work in Malleswaram 8th cross") == "Malleshwaram"
    assert extract_area("Shifted to Rajajinagar") == "Rajajinagar"


def test_pay_extraction():
    """5. Test extraction of pay in various formats."""
    assert extract_pay("Payment is 800 rupees per day") == 800.0
    assert extract_pay("Offering ₹ 950 daily") == 950.0
    assert extract_pay("Salary: Rs. 1200 per day") == 1200.0
    assert extract_pay("Rate of 750/- for full day") == 750.0
    assert extract_pay("pay 600 roj ka") == 600.0


def test_duration_extraction():
    """6. Test extraction of job duration."""
    assert extract_duration("Need someone for 3 days") == "3 days"
    assert extract_duration("Requirement is for 2 weeks") == "2 weeks"
    assert extract_duration("Need helper for 1 day only") == "1 days" or extract_duration("Need helper for 1 day only") == "1 day"
    assert extract_duration("Full time position") == "Full time"
    assert extract_duration("Kaam 4 din chalega") == "4 days"


def test_missing_skill_handling():
    """7. Test handling when skill is missing in user input."""
    result = extract_job_details("I am looking for work in Hebbal")
    assert result["skill"] is None
    assert result["area"] == "Hebbal"
    assert "skill" in result["missing_fields"]
    assert result["is_complete"] is False
    assert result["follow_up_question"] is not None
    assert "skill" in result["follow_up_question"].lower()


def test_missing_location_handling():
    """8. Test handling when location is missing in user input."""
    result = extract_job_details("I need an electrician for 2 days paying 800 rupees")
    assert result["skill"] == "Electrician"
    assert result["area"] is None
    assert "area" in result["missing_fields"]
    assert result["pay"] == 800.0
    assert result["is_complete"] is False
    assert result["follow_up_question"] is not None
    assert "bengaluru locality" in result["follow_up_question"].lower()
