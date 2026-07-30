# LASTMA Traffic Map Portal

A live web portal that extracts traffic reports from the official LASTMA X account **@followlastma** and displays them in:

- **Dashboard** – counts of total reports, breakdowns, incidents, areas affected, severe events
- **Interactive Map** – Leaflet map with colour-coded markers for each occurrence in Lagos
- **Structured Table** – time, location, type, summary, impact, and link to the original post

## Features

| Feature | Description |
|---------|-------------|
| Live X API | Fetches recent posts via Twitter/X API v2 Recent Search |
| Mock mode | Rich sample data when no Bearer Token is configured |
| Caching | 2-minute in-memory cache to respect rate limits |
| Auto-refresh | Frontend reloads data every 3 minutes |
| Zero external DB | Pure Python + static HTML |

## Quick Start (local)

```bash
# 1. Clone / copy the project
cd lastma-portal

# 2. Install dependency (only httpx needed)
pip install -r requirements.txt

# 3. Run in mock mode (no API key required)
cd backend
python main.py
```

Open **http://localhost:8080** in your browser.

### Live mode (X API)

1. Create a developer account at [https://developer.x.com](https://developer.x.com)
2. Create a Project + App and generate a **Bearer Token**
3. Note: Free tier has extremely limited Recent Search access.  
   Basic ($100/mo) or Pro is recommended for reliable production use.

```bash
export X_BEARER_TOKEN="your_bearer_token_here"
export PORT=8080          # optional
python main.py
```

The UI will show a green **LIVE** badge when the API is successfully used.

## Project Structure

```
lastma-portal/
├── backend/
│   ├── main.py          # HTTP server + API routes
│   ├── config.py        # Environment configuration
│   └── x_client.py      # X API client + mock data + location geocoding
├── frontend/
│   └── index.html       # Single-page app (dashboard + map + table)
├── requirements.txt
├── Dockerfile
└── README.md
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Frontend UI |
| GET | `/api/reports` | List of traffic reports (JSON) |
| GET | `/api/stats` | Aggregated dashboard statistics |
| GET | `/api/health` | Health check |

Example response from `/api/reports`:

```json
{
  "source": "live",
  "count": 12,
  "reports": [
    {
      "id": "2082736716385783909",
      "time": "08:48",
      "date": "2026-07-30",
      "location": "Agege Motor Rd – Airport Bus Stop",
      "area": "Agege / Ikeja",
      "type": "Breakdown",
      "summary": "Broken down 22-tyre truck…",
      "impact": "Minimal",
      "lat": 6.585,
      "lng": 3.338,
      "url": "https://x.com/followlastma/status/2082736716385783909"
    }
  ]
}
```

## Deployment

### Option A – Render.com (recommended free tier)

1. Push this folder to a GitHub repository.
2. Go to [render.com](https://render.com) → **New → Web Service**.
3. Connect the repo.
4. Settings:
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `cd backend && python main.py`
   - **Environment Variables**:
     - `X_BEARER_TOKEN` = your token (optional – works in mock mode without it)
     - `PORT` = `10000` (Render sets this automatically; the app reads `$PORT`)
5. Deploy. Your app will be live at `https://your-service.onrender.com`.

### Option B – Railway

1. `railway login` / connect GitHub
2. New Project → Deploy from repo
3. Set start command: `cd backend && python main.py`
4. Add `X_BEARER_TOKEN` in Variables

### Option C – Docker

```bash
docker build -t lastma-portal .
docker run -p 8080:8080 -e X_BEARER_TOKEN=your_token lastma-portal
```

### Option D – Fly.io / any VPS

Same pattern: install Python deps, set env vars, run `python backend/main.py`.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `X_BEARER_TOKEN` | (empty) | X API v2 Bearer Token. Empty → mock mode |
| `X_USERNAME` | `followlastma` | Account to fetch posts from |
| `MAX_RESULTS` | `30` | Number of posts to request |
| `CACHE_SECONDS` | `120` | How long to cache live results |
| `PORT` | `8080` | HTTP port |
| `HOST` | `0.0.0.0` | Bind address |

## Notes & Limitations

- **X API pricing**: Recent Search on the Free tier is severely restricted (or unavailable depending on current policy). Budget for Basic tier if you need reliable live data.
- **Location geocoding**: Approximate coordinates are derived from a built-in Lagos location dictionary + hashtag parsing. You can extend `LOCATION_COORDS` in `x_client.py`.
- **Rate limits**: The backend caches responses for 2 minutes by default.
- **Not official**: This is an independent community tool and is not affiliated with LASTMA or the Lagos State Government.

## Extending

- Add more locations to `LOCATION_COORDS` in `backend/x_client.py`
- Switch to FastAPI + Uvicorn for production (uncomment in `requirements.txt` and rewrite the server)
- Add a SQLite/Postgres store to keep historical reports
- Add Chart.js visualisations on the dashboard

---

Built for monitoring Lagos traffic reports from @followlastma.
