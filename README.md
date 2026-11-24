# TASKORA
> **Say your skill. Find work nearby.**

**Hackathon:** wHACKiest 2026  
**Track:** Track 4 – UnlockED  
**Problem Statement:** Hyper-Local Job Matching for Informal & Semi-Skilled Workers  
**Repository Name:** `taskora`

---

## 1. Problem Statement

Informal and semi-skilled workers (electricians, plumbers, painters, carpenters, masons, drivers, cooks, cleaners, helpers, security guards) often struggle to find consistent nearby employment opportunities. Many workers face high digital friction:
- Language barriers and complex mobile applications.
- Text-heavy digital job platforms requiring resumes, email signups, and credit cards.
- Lack of localized, distance-aware job matching.

Simultaneously, small employers, homeowners, and local contractors face recurring challenges finding nearby informal workers quickly. 

## 2. Proposed Solution

**TASKORA** is a voice-first, hyper-local job matching platform connecting informal workers with local employers through natural voice and text interactions in **English, Hindi, and Kannada**.

Workers can simply press a microphone and speak:
> *"I am an electrician looking for work near Hebbal."*
> or
> *"मुझे कोरमंगला में पेंटर का काम चाहिए।"*

Employers can post open requirements by voice:
> *"I need a plumber in Whitefield for 3 days. Payment is 800 rupees per day."*

TASKORA deterministically extracts the skill, locality, pay, and duration, calculates geographical distance using the Haversine formula, and ranks matching opportunities transparently.

---

## 3. Key Features

- **Voice-First Input:** Web Speech API integration in browser with speech recognition in English, Hindi, and Kannada and editable transcript fallback.
- **Deterministic Natural Language Extraction:** Zero-cost, fast extraction of trade skills, Bengaluru localities, pay amounts, and duration without black-box LLM dependencies.
- **Hyper-Local Matching:** Exact skill matching coupled with the Haversine great-circle distance algorithm within a configurable search radius (default: 10–15 km).
- **Multi-Factor Transparent Scoring:** Weighted formula accounting for skill match, physical proximity, job recency, and daily pay.
- **Community Safety & Reporting:** Instant one-click reporting mechanism that automatically flags and hides listings with 3 or more reports.
- **Text-to-Speech (TTS) with Fallback:** Audio job summaries powered by the ElevenLabs API with disk caching, seamlessly falling back to browser `speechSynthesis` if API keys are absent.
- **Accessible, Mobile-First Design:** High-contrast buttons, large touch targets, English, Hindi, and Kannada interface, and zero frontend framework build dependencies.

---

## 4. Technology Stack

- **Backend:** Python 3.11+, FastAPI, Uvicorn, Pydantic
- **Database:** SQLite3 (Python standard library `sqlite3`), strictly parameterized SQL queries (no ORM)
- **Frontend:** HTML5, CSS3, Vanilla JavaScript (zero node build tools, pure browser Web APIs)
- **Voice & Speech:**
  - Speech Input: Browser Web Speech API (`SpeechRecognition` / `webkitSpeechRecognition`)
  - Speech Output: ElevenLabs API (`eleven_multilingual_v2`) with SHA-256 disk caching & browser `speechSynthesis` fallback
- **Testing:** pytest

---

## 5. System Architecture

```
[ Worker / Employer ]
        │
   (Voice / Text)
        │
        ▼
[ Web Frontend (HTML5/CSS3/Vanilla JS) ]
   ├── Web Speech Recognition (en-IN, hi-IN, kn-IN)
   ├── Responsive Job Cards & Audio Player
   └── Web SpeechSynthesis Fallback
        │
     (REST HTTP)
        │
        ▼
[ FastAPI Backend (app/main.py) ]
   ├── Natural Language Extractor (app/extract.py)
   │     └── Multilingual Keyword Dictionary & Regex
   ├── Hyper-Local Matcher (app/matcher.py)
   │     └── Haversine Formula + 4-Factor Weighted Ranking
   ├── Voice Service (app/voice.py)
   │     └── ElevenLabs Client + SHA-256 Disk Cache
   └── Database Layer (app/db.py)
         └── SQLite3 (Parameterized Queries & Seed Data)
```

---

## 6. Database Design

Database file: `data/taskora.db` (auto-created on startup)

### `jobs` Table Schema

| Field | Type | Description |
|---|---|---|
| `id` | `INTEGER PRIMARY KEY AUTOINCREMENT` | Unique job identifier |
| `skill` | `TEXT NOT NULL` | Normalized trade skill (e.g. `Electrician`) |
| `description` | `TEXT` | Job summary or employer notes |
| `area` | `TEXT NOT NULL` | Bengaluru locality name |
| `latitude` | `REAL NOT NULL` | Latitude coordinate |
| `longitude` | `REAL NOT NULL` | Longitude coordinate |
| `pay` | `REAL` | Daily pay rate in INR |
| `duration` | `TEXT` | Job duration (e.g. `1 day`, `3 days`) |
| `employer_name` | `TEXT NOT NULL` | Employer or business name |
| `employer_phone` | `TEXT NOT NULL` | Contact phone number |
| `created_at` | `TEXT NOT NULL` | ISO 8601 UTC creation timestamp |
| `status` | `TEXT NOT NULL DEFAULT 'open'` | Job status (`open`, `closed`, `flagged`) |
| `report_count` | `INTEGER NOT NULL DEFAULT 0` | Abuse/error report count |

Seed data: 20 demonstration listings across 10 skills in Bengaluru with fictional phone numbers `9000000001` to `9000000020`.

---

## 7. Matching Algorithm & Scoring Formula

The matching algorithm (`app/matcher.py`) filters jobs by:
1. `status == 'open'`
2. `report_count < 3`
3. Exact normalized skill match
4. Haversine distance $\le$ `max_radius_km` (default 10 km)

### Haversine Formula

$$\Delta\phi = \phi_2 - \phi_1,\quad \Delta\lambda = \lambda_2 - \lambda_1$$
$$a = \sin^2\left(\frac{\Delta\phi}{2}\right) + \cos(\phi_1)\cos(\phi_2)\sin^2\left(\frac{\Delta\lambda}{2}\right)$$
$$c = 2 \cdot \text{atan2}(\sqrt{a}, \sqrt{1-a}),\quad d = R \cdot c \quad (R = 6371.0\text{ km})$$

### Weighted Scoring Formula

$$\text{Final Score} = 0.5 \times S + 0.3 \times D + 0.1 \times R + 0.1 \times P$$

- **Skill Score ($S$):** $1.0$ (matching skill), $0$ otherwise.
- **Distance Score ($D$):** $\max\left(0, 1 - \frac{\text{distance}}{\text{max\_radius}}\right)$
- **Recency Score ($R$):** $\max\left(0, 1 - \frac{\text{age\_days}}{7.0}\right)$ (decays linearly over 7 days).
- **Pay Fit Score ($P$):** $\frac{\text{candidate\_pay}}{\text{max\_pay\_among\_eligible}}$

Results are ranked descending by Final Score; top 5 matching jobs are returned.

---

## 8. Supported Localities & Skills

### Localities (Bengaluru)
1. Yelahanka
2. Hebbal
3. Malleshwaram
4. Rajajinagar
5. Yeshwanthpur
6. Peenya
7. Jayanagar
8. Koramangala
9. Whitefield
10. Marathahalli
11. Banashankari
12. Electronic City

*Note: Coordinates in `data/areas.json` represent approximate center coordinates for demonstration.*

### Skills & Trade Dictionary
1. Electrician (bijli wala, बिजली मिस्त्री)
2. Plumber (nal wala, नल मिस्त्री)
3. Painter (rang wala, पेंटर)
4. Carpenter (badhai, बढ़ई)
5. Mason (raj mistri, राज मिस्त्री)
6. Driver (chalak, गाड़ी चालक)
7. Cook (rasoiya, खाना बनाने वाला)
8. Cleaner (safai karmi, सफाई वाला)
9. Helper (madadgar, मजदूर)
10. Security Guard (chowkidar, गार्ड)

---

## 9. Installation & Setup

### Prerequisites
- Python 3.11+
- Git

### Clone & Install
```bash
git clone https://github.com/Chirantan112/whackiest.git
cd whackiest

# Create virtual environment (optional but recommended)
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Environment Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Contents of `.env`:
```ini
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM
ELEVENLABS_MODEL_ID=eleven_multilingual_v2
HOST=127.0.0.1
PORT=8000
```
> **Note:** TASKORA runs seamlessly with client-side Web Speech fallback even if `ELEVENLABS_API_KEY` is left blank!

---

## 10. Running the Application

Start the FastAPI application with Uvicorn:
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
Open your browser at:
- **Landing Page:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Worker Search:** [http://127.0.0.1:8000/worker](http://127.0.0.1:8000/worker)
- **Employer Post:** [http://127.0.0.1:8000/employer](http://127.0.0.1:8000/employer)
- **Interactive Swagger Docs:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## 11. API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Serves Landing Page (`web/index.html`) |
| `GET` | `/worker` | Serves Worker Page (`web/worker.html`) |
| `GET` | `/employer` | Serves Employer Page (`web/employer.html`) |
| `GET` | `/api/health` | Health status and open jobs count |
| `GET` | `/api/areas` | List of supported localities and approximate coordinates |
| `GET` | `/api/skills` | Supported skills and dictionary aliases |
| `POST` | `/api/parse` | Natural language text extraction (skill, area, pay, duration) |
| `GET` | `/api/jobs/search` | Search ranked jobs by skill and area (`?skill=Electrician&area=Hebbal`) |
| `POST` | `/api/jobs` | Post a new job listing |
| `POST` | `/api/jobs/{id}/report` | Report a job listing (increments report count; flags at 3) |
| `POST` | `/api/tts` | ElevenLabs text-to-speech with disk caching & fallback |

---

## 12. Running Tests

Run the full pytest suite:
```bash
pytest tests -v
```
The test suite covers:
- `tests/test_extract.py`: English, Devanagari Hindi, Romanized Hindi, area, pay, duration, and missing fields.
- `tests/test_matcher.py`: Haversine calculation, proximity ranking, pay fit, closed and reported jobs exclusion.
- `tests/test_api.py`: FastAPI routes, validation, search, report, and TTS fallback.
- `tests/test_frontend.py`: HTML pages, status codes, branding, disclaimers, and interactive elements.
- `tests/test_voice.py`: Language-aware deterministic hashing, disk cache retrieval, empty input handling, and safe API/network fallback behavior.

---

## 13. Project Structure

```
taskora/
│
├── app/
│   ├── main.py         # FastAPI routes, static mounting, life-cycle
│   ├── db.py           # SQLite connection, schema init, seed data loader
│   ├── extract.py      # Multilingual natural-language parser
│   ├── matcher.py      # Haversine distance & 4-factor scoring
│   └── voice.py        # ElevenLabs TTS & disk caching
│
├── web/
│   ├── index.html      # Landing page (I Need Work / I Need a Worker)
│   ├── worker.html     # Worker voice search & job cards
│   ├── employer.html   # Employer voice/text post & review form
│   ├── app.js          # Web Speech API, TTS player, REST API calls
│   └── style.css       # Responsive, high-contrast, accessible CSS
│
├── data/
│   ├── seed_jobs.json  # 20 realistic Bengaluru demonstration jobs
│   └── areas.json      # 12 Bengaluru localities with coordinates
│
├── tests/
│   ├── test_matcher.py # Distance & ranking algorithm tests
│   ├── test_extract.py # Multilingual extraction tests
│   ├── test_api.py     # FastAPI endpoints tests
│   ├── test_frontend.py# HTML UI & asset tests
│   └── test_voice.py   # Audio hashing & caching tests
│
├── audio_cache/        # Cached TTS MP3 files (.gitkeep tracked)
├── requirements.txt    # Python dependencies
├── .env.example        # Environment template
├── .gitignore          # Git exclusion rules
└── README.md           # Documentation
```

---

## 14. Current Limitations & Honest Disclaimers

- **Approximate Locality Coordinates:** Center coordinates are demonstration coordinates for Bengaluru localities, not precise real-time GPS tracking.
- **Demo Data Disclaimer:** Seed listings are demonstration data. Employer identity and criminal background verification are not implemented yet.
- **Language Scope:** Currently optimized for English, Hindi, and Kannada. Speech recognition and text parsing support Kannada; availability of Kannada speech recognition and speech voices depends on the browser and device.

---

## 15. Future Enhancements

1. **OTP-Verified Employers:** Phone verification via SMS OTP to prevent fraudulent job postings.
2. **WhatsApp Integration:** Direct job alerts and voice note submissions via the WhatsApp Business API.
3. **Missed-Call & IVR Support:** Interactive voice response (IVR) phone hotline for workers with basic feature phones (no smartphone required).
4. **Additional Indian Languages:** Extend voice recognition and localized parsing to more regional languages.
5. **Worker Profiles & Peer Ratings:** Community badges and verified job completion history.
6. **Geohash Proximity Matching:** Ultra-fast sub-kilometer clustering using geohashes.

---

## 16. Contributors

- Developed for **wHACKiest 2026** — Track 4: UnlockED
- Open-source under MIT License.
