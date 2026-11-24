"""
TASKORA - Natural Language Extraction Module
Extracts skill, area, pay amount, and duration deterministically from text.
Supports English, Devanagari Hindi, Romanized Hindi, and Kannada.
Does not guess or use expensive external LLM APIs, keeping it beginner-friendly, fast, and transparent.
"""

import re
from typing import Any, Dict, List, Optional
from app.db import load_areas

# Skill keywords mapping canonical skill to aliases (English, Hindi, Romanized Hindi, and Kannada)
SKILL_DICTIONARY: Dict[str, List[str]] = {
    "Electrician": [
        "electrician", "bijli wala", "bijli", "bijli mistri", "bijli mistry",
        "बिजली वाला", "बिजली मिस्त्री", "बिजली", "इलेक्ट्रीशियन", "इलेक्ट्रिशियन",
        "electric work", "wiring", "ವಿದ್ಯುತ್ ಕೆಲಸ", "ಎಲೆಕ್ಟ್ರಿಷಿಯನ್", "ವೈರಿಂಗ್"
    ],
    "Plumber": [
        "plumber", "nal wala", "nal mistri", "nal mistry", "pipe fitter",
        "नल वाला", "नल मिस्त्री", "प्लम्बर", "प्लंबर", "नल", "leakage", "ಕೊಳಾಯಿ ಕೆಲಸ", "ಪ್ಲಂಬರ್", "ನಳ ಕೆಲಸ"
    ],
    "Painter": [
        "painter", "rang wala", "rang mistri", "putty wala", "wall painter",
        "पेंटर", "रंग वाला", "रंग मिस्त्री", "पुट्टी", "रंगाई", "ಬಣ್ಣದ ಕೆಲಸ", "ಪೇಂಟರ್", "ಬಣ್ಣ ಹಚ್ಚುವವರು"
    ],
    "Carpenter": [
        "carpenter", "badhai", "badhi", "lakdi wala", "furniture maker",
        "बढ़ई", "बढई", "कारपेंटर", "लकड़ी वाला", "ಫರ್ನಿಚರ್", "ಮರಗೆಲಸ", "ಬಡಗಿ", "ಫರ್ನಿಚರ್"
    ],
    "Mason": [
        "mason", "raj mistri", "raj mistry", "rajgeer", "masonry", "bricklayer",
        "राज मिस्त्री", "राजमिस्त्री", "राजगीर", "मिस्त्री", "राज मिस्त्री", "ಕಟ್ಟಡ ಕೆಲಸ", "ಮೇಸ್ತ್ರಿ", "ರಾಜಮೇಸ್ತ್ರಿ"
    ],
    "Driver": [
        "driver", "gadi chalak", "chalak", "cab driver", "auto driver", "car driver",
        "ड्राइवर", "चालक", "गाड़ी चालक", "गाड़ी चालक", "ड्राइविंग", "ಚಾಲಕ", "ಡ್ರೈವರ್", "ಗಾಡಿ ಚಾಲಕ"
    ],
    "Cook": [
        "cook", "rasoiya", "khana banane wala", "khana banane wali", "chef", "bavarchi",
        "रसोइया", "रसोईया", "खाना बनाने वाला", "खाना बनाने वाली", "कुक", "ಬಾಣಸಿಗ", "ಅಡುಗೆ ಕೆಲಸ", "ಅಡುಗೆಯವರು", "ಕುಕ್"
    ],
    "Cleaner": [
        "cleaner", "safai karmi", "safai wala", "safai wali", "sweeper", "housekeeping",
        "सफाई वाला", "सफाई वाली", "सफाई कर्मी", "सफाई", "क्लीनर", "झाड़ू पोछा", "ಸ್ವಚ್ಛತಾ ಕೆಲಸ", "ಕ್ಲೀನರ್", "ಸಫಾಯಿ ಕೆಲಸ"
    ],
    "Helper": [
        "helper", "madadgar", "labour", "mazdoor", "loading", "unloading", "peon",
        "हेल्पर", "मददगार", "मजदूर", "मज़दूर", "लेबर", "ಕೂಲಿ", "ಸಹಾಯಕ", "ಕೆಲಸದ ಸಹಾಯಕ", "ಹೆಲ್ಪರ್"
    ],
    "Security Guard": [
        "security guard", "guard", "chowkidar", "chaukidar", "watchman",
        "सिक्योरिटी गार्ड", "गार्ड", "चौकीदार", "सुरक्षा गार्ड", "ವಾಚಮನ್", "ಕಾವಲುಗಾರ", "ಭದ್ರತಾ ಸಿಬ್ಬಂದಿ", "ಸೆಕ್ಯೂರಿಟಿ ಗಾರ್ಡ್"
    ]
}


def normalize_text(text: str) -> str:
    """Lowercases and cleans extra whitespace."""
    if not text:
        return ""
    return " ".join(text.lower().split())


def extract_skill(text: str) -> Optional[str]:
    """
    Finds matching skill from English, Hindi, Romanized Hindi, or Kannada keywords.
    Prioritizes longer keyword matches to avoid substring overlaps.
    """
    clean_input = normalize_text(text)
    if not clean_input:
        return None

    # Flatten mapping with length sorting so e.g. "security guard" matches before "guard"
    sorted_patterns = []
    for canonical, aliases in SKILL_DICTIONARY.items():
        for alias in aliases:
            sorted_patterns.append((alias.lower(), canonical))
    sorted_patterns.sort(key=lambda x: len(x[0]), reverse=True)

    for alias, canonical in sorted_patterns:
        is_ascii = all(ord(c) < 128 for c in alias)
        if is_ascii:
            pattern = r'\b' + re.escape(alias) + r'\b'
            if re.search(pattern, clean_input):
                return canonical
        else:
            if alias in clean_input:
                return canonical

    return None


def extract_area(text: str, custom_areas: Optional[List[Dict[str, Any]]] = None) -> Optional[str]:
    """
    Matches Bengaluru localities from the text using canonical names and aliases.
    """
    clean_input = normalize_text(text)
    if not clean_input:
        return None

    areas_list = custom_areas if custom_areas is not None else load_areas()
    sorted_areas = []

    for item in areas_list:
        canonical = item["name"]
        aliases = item.get("aliases", []) + [canonical]
        for alias in aliases:
            sorted_areas.append((alias.lower(), canonical))

    # Match longer names first (e.g. "electronic city phase 1" before "electronic city")
    sorted_areas.sort(key=lambda x: len(x[0]), reverse=True)

    for alias, canonical in sorted_areas:
        is_ascii = all(ord(c) < 128 for c in alias)
        if is_ascii:
            pattern = r'\b' + re.escape(alias) + r'\b'
            if re.search(pattern, clean_input):
                return canonical
        else:
            if alias in clean_input:
                return canonical

    return None


def extract_pay(text: str) -> Optional[float]:
    """
    Extracts pay amount from common currency representations:
    Examples: '₹800', 'Rs 750', '800 rupees', 'pay 1000', '900 per day', '800/-'
    """
    clean_input = text.replace(",", "")

    # Patterns matching currency prefix or suffix
    patterns = [
        # ₹ 800 or Rs. 800 or Rs 800 or INR 800
        r'(?:₹|rs\.?|inr)\s*([0-9]+(?:\.[0-9]+)?)',
        # 800 rupees / 800 rupaye / 800 rs
        r'([0-9]+(?:\.[0-9]+)?)\s*(?:rupees|rupaye|rupayee|rs|₹|/-)',
        # pay 800 / payment 800 / salary 800 / dega 800
        r'(?:pay|payment|rate|salary|dega|milenge)\s*(?:is|of|:)?\s*([0-9]+(?:\.[0-9]+)?)',
        # 800 per day / 800 daily / 800 roj ka
        r'([0-9]+(?:\.[0-9]+)?)\s*(?:per\s*day|daily|roj\s*ka|pratidin)'
    ]

    for pat in patterns:
        match = re.search(pat, clean_input, re.IGNORECASE)
        if match:
            try:
                val = float(match.group(1))
                if val > 0:
                    return val
            except (ValueError, IndexError):
                continue

    return None


def extract_duration(text: str) -> Optional[str]:
    """
    Extracts job duration:
    Examples: '3 days', '1 day', '2 weeks', '1 month', 'daily', '1 din', '2 hafte'
    """
    clean_input = normalize_text(text)

    # Number + unit (days, weeks, months, hours, din, hafte, mahine)
    pattern = r'(\b\d+\s*(?:days?|weeks?|months?|hours?|hrs?|din|hafte|mahine)\b)'
    match = re.search(pattern, clean_input, re.IGNORECASE)
    if match:
        dur = match.group(1)
        # Standardize romanized hindi terms to english for clean UI display
        dur = re.sub(r'\bdin\b', 'days', dur)
        dur = re.sub(r'\bhafte\b', 'weeks', dur)
        dur = re.sub(r'\bmahine\b', 'months', dur)
        return dur

    # Single words
    if re.search(r'\b(full\s*time|fulltime)\b', clean_input):
        return "Full time"
    if re.search(r'\b(part\s*time|parttime)\b', clean_input):
        return "Part time"
    if re.search(r'\b(daily|pratidin|roj)\b', clean_input):
        return "Daily"

    return None


def extract_job_details(text: str, custom_areas: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """
    Main extraction function for natural language input.
    Extracts skill, area, pay, and duration.
    Determines missing fields and generates appropriate follow-up prompt.
    """
    skill = extract_skill(text)
    area = extract_area(text, custom_areas=custom_areas)
    pay = extract_pay(text)
    duration = extract_duration(text)

    missing_fields = []
    if not skill:
        missing_fields.append("skill")
    if not area:
        missing_fields.append("area")

    # Generate friendly follow-up question if required fields are missing
    follow_up_question = None
    if "skill" in missing_fields and "area" in missing_fields:
        follow_up_question = "What work or skill are you looking for, and in which Bengaluru area? (e.g., 'Electrician in Hebbal')"
    elif "skill" in missing_fields:
        follow_up_question = "Which skill or trade do you need? (e.g., Plumber, Carpenter, Painter, Driver)"
    elif "area" in missing_fields:
        follow_up_question = f"Which Bengaluru locality near {skill}? (e.g., Koramangala, Whitefield, Hebbal)"

    return {
        "raw_text": text,
        "skill": skill,
        "area": area,
        "pay": pay,
        "duration": duration,
        "missing_fields": missing_fields,
        "is_complete": len(missing_fields) == 0,
        "follow_up_question": follow_up_question
    }
