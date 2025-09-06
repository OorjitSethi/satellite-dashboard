# Satellite Ground Track Dashboard

A full-stack project for visualizing satellite ground tracks using TLE (Two-Line Element) data.

## Overview
- **Frontend:** React (Plotly for visualization)
- **Backend:** Flask (Python) with SGP4 & numerical utilities
- **Purpose:** Search satellites, fetch / refresh TLEs, propagate orbits, and display ground tracks with azimuth coloring.

## Features
- Satellite name search (local cached database populated from CelesTrak or optional local catalog file)
- Direct TLE input mode
- SGP4 propagation with automatic TLE staleness handling
- Colored ground track by azimuth, start & end markers
- Returns metadata (start/end UTC, TLE epoch & age)

## Project Structure
```
backend/
  app.py              # Flask API
  requirements.txt    # Python dependencies
  data/tle_catalog.txt (optional local catalog)
frontend/
  package.json        # React dependencies
  src/                # React components
```

## Quick Start
### 1. Clone the repository
```bash
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>
```

### 2. Backend setup (Python 3.10+ recommended)
```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
python app.py
```
Backend runs on http://127.0.0.1:5000

### 3. Frontend setup
Open a second terminal:
```bash
cd frontend
npm install
npm start
```
Frontend runs on http://localhost:3000 and talks to backend on port 5000.

## Environment Variables (Optional)
- `TLE_FILE`: Path to a local multi-satellite TLE catalog (3-line format: name + two lines). If present it loads instantly; otherwise the app fetches from CelesTrak groups.

## API Endpoints (Summary)
- `POST /api/get-tle` – Body: `{ "satellite_name": "ISS" }`
- `GET /api/search-satellites?q=iss&limit=20`
- `POST /api/propagate` – Provide raw TLE: `{ line1, line2, duration }`
- `POST /api/propagate-by-name` – `{ satellite_name, duration }`

All propagation responses include:
```
{
  times_hr: [...],
  latitudes: [...],
  longitudes: [...],
  azimuths: [...],
  start_utc_iso, end_utc_iso,
  tle_epoch_iso, tle_age_hours, anchored_to_tle_epoch
}
```

## GitHub Deployment Checklist
1. Create a new repo on GitHub (no README / .gitignore so this one can push cleanly)
2. Initialize locally (commands below) and push
3. Add badges, license, or CI later as needed

### Initial Push Commands
From project root:
```bash
git init
git add .
git commit -m "Initial commit: Satellite Ground Track Dashboard"
git branch -M main
git remote add origin git@github.com:<your-username>/<your-repo>.git
# or: https://github.com/<your-username>/<your-repo>.git
git push -u origin main
```

## Common Issues
| Symptom | Cause | Fix |
|--------|-------|-----|
| Long first request | Satellite DB fetching groups remotely | Wait; subsequent searches are fast |
| 500 error propagate | TLE outdated/invalid | Fetch fresh TLE via `/api/get-tle` |
| Track looks stationary | Very old or GEO satellite with small apparent motion in short window | Increase duration or verify TLE freshness |

## Next Ideas
- Add altitude / ground track animation
- Cache TLE refresh results to disk
- Add Dockerfile & docker-compose
- Add basic tests (pytest + React testing library)

---
MIT License (add a LICENSE file if you plan to open source)
