"""
X (Twitter) API v2 client for fetching posts from @followlastma.

Uses the official Recent Search endpoint.
Requires a Bearer Token from https://developer.x.com

Falls back to mock data when no token is configured or the API is unavailable.
"""
from __future__ import annotations

import re
import time
from datetime import datetime, timezone
from typing import Any

import httpx

from config import CACHE_SECONDS, MAX_RESULTS, X_BEARER_TOKEN, X_USERNAME

# Simple in-memory cache
_cache: dict[str, Any] = {"data": None, "expires": 0.0}


# ---------------------------------------------------------------------------
# Mock data (used when no X_BEARER_TOKEN is set)
# ---------------------------------------------------------------------------
MOCK_REPORTS = [
    {
        "id": "2082736716385783909",
        "time": "08:48",
        "date": "2026-07-30",
        "timestamp": "2026-07-30T07:55:03Z",
        "location": "Agege Motor Rd – Airport Bus Stop",
        "area": "Agege / Ikeja",
        "type": "Breakdown",
        "summary": "Broken down 22-tyre truck at Airport Bus stop inward National Flyover. Cones placed, recovery in progress.",
        "impact": "Minimal",
        "lat": 6.585,
        "lng": 3.338,
        "url": "https://x.com/followlastma/status/2082736716385783909",
        "media": True,
    },
    {
        "id": "2082721420723843230",
        "time": "07:50",
        "date": "2026-07-30",
        "timestamp": "2026-07-30T06:54:16Z",
        "location": "Ikorodu – Okegbegun",
        "area": "Ikorodu",
        "type": "Incident",
        "summary": "Flat-body truck spilled contents + 40ft container truck brake failure collision. ~90% access denied. Crane/tow expected.",
        "impact": "Severe",
        "lat": 6.615,
        "lng": 3.505,
        "url": "https://x.com/followlastma/status/2082721420723843230",
        "media": True,
    },
    {
        "id": "2082719629546307962",
        "time": "07:35",
        "date": "2026-07-30",
        "timestamp": "2026-07-30T06:47:09Z",
        "location": "Surulere – Abebe Village / Brewery",
        "area": "Surulere",
        "type": "Breakdown",
        "summary": "Loaded containerized truck rear tyre problem at Abebe Village by Brewery inward Eric Moore. Repair ongoing.",
        "impact": "Controlled",
        "lat": 6.492,
        "lng": 3.355,
        "url": "https://x.com/followlastma/status/2082719629546307962",
        "media": True,
    },
    {
        "id": "2082711814601601185",
        "time": "07:10",
        "date": "2026-07-30",
        "timestamp": "2026-07-30T06:16:06Z",
        "location": "Orile – Doyin",
        "area": "Orile / Apapa",
        "type": "Incident",
        "summary": "20ft containerized truck stuck on BRT demarcation at Doyin inward Orile. Tow vehicle on ground.",
        "impact": "Low",
        "lat": 6.458,
        "lng": 3.345,
        "url": "https://x.com/followlastma/status/2082711814601601185",
        "media": True,
    },
    {
        "id": "2082699145731523023",
        "time": "06:06",
        "date": "2026-07-30",
        "timestamp": "2026-07-30T05:25:45Z",
        "location": "Outer Marina – Train Station",
        "area": "Lagos Island",
        "type": "Incident",
        "summary": "Mack flatbed loaded with iron rods hooked on BRT median by Train Station, Marina. Tow contacted.",
        "impact": "Low",
        "lat": 6.452,
        "lng": 3.392,
        "url": "https://x.com/followlastma/status/2082699145731523023",
        "media": True,
    },
    {
        "id": "2082681084630741144",
        "time": "04:56",
        "date": "2026-07-30",
        "timestamp": "2026-07-30T04:13:59Z",
        "location": "Eko Bridge inward Apongbon",
        "area": "Lagos Island / Mainland",
        "type": "Breakdown",
        "summary": "Loaded 20ft container truck broken spring on Eko Bridge. On-spot repair ongoing, cones placed.",
        "impact": "Moderate",
        "lat": 6.455,
        "lng": 3.385,
        "url": "https://x.com/followlastma/status/2082681084630741144",
        "media": True,
    },
    {
        "id": "2082494369932738737",
        "time": "16:40",
        "date": "2026-07-29",
        "timestamp": "2026-07-29T15:52:03Z",
        "location": "Victoria Island – Bar Beach / Bonny Camp",
        "area": "Victoria Island",
        "type": "Incident",
        "summary": "Road crash involving two flat-bed trucks at Bar-Beach front inward Bonny Camp. One lane affected.",
        "impact": "Low",
        "lat": 6.428,
        "lng": 3.421,
        "url": "https://x.com/followlastma/status/2082494369932738737",
        "media": True,
    },
    {
        "id": "2082488536226209859",
        "time": "16:25",
        "date": "2026-07-29",
        "timestamp": "2026-07-29T15:28:52Z",
        "location": "Egbeda – Baale / Oniwaya",
        "area": "Egbeda",
        "type": "Incident",
        "summary": "Mini truck stuck in drainage while reversing to offload at Baale inward Oniwaya. Recovery ongoing.",
        "impact": "Moderate",
        "lat": 6.595,
        "lng": 3.298,
        "url": "https://x.com/followlastma/status/2082488536226209859",
        "media": True,
    },
    {
        "id": "2082487299766415774",
        "time": "16:18",
        "date": "2026-07-29",
        "timestamp": "2026-07-29T15:23:57Z",
        "location": "Oshodi Bridge inward Anthony",
        "area": "Oshodi",
        "type": "Breakdown",
        "summary": "Loaded truck broke down ascending Oshodi Bridge inward Anthony. One lane taken.",
        "impact": "Moderate",
        "lat": 6.555,
        "lng": 3.345,
        "url": "https://x.com/followlastma/status/2082487299766415774",
        "media": True,
    },
    {
        "id": "2082479040611430722",
        "time": "15:47",
        "date": "2026-07-29",
        "timestamp": "2026-07-29T14:51:08Z",
        "location": "Agbara Car Wash – Lagos-Badagry Exp Way",
        "area": "Agbara / Badagry",
        "type": "Breakdown",
        "summary": "Loaded Mack containerized truck mechanical fault at Agbara Car Wash inward Badagry. Not affecting flow.",
        "impact": "None",
        "lat": 6.508,
        "lng": 3.095,
        "url": "https://x.com/followlastma/status/2082479040611430722",
        "media": True,
    },
]


# ---------------------------------------------------------------------------
# Location dictionary (approximate coordinates for common LASTMA locations)
# ---------------------------------------------------------------------------
LOCATION_COORDS: dict[str, tuple[float, float, str]] = {
    # key substring → (lat, lng, friendly area)
    "agege": (6.585, 3.338, "Agege / Ikeja"),
    "airport": (6.585, 3.338, "Agege / Ikeja"),
    "ikorodu": (6.615, 3.505, "Ikorodu"),
    "okegbegun": (6.615, 3.505, "Ikorodu"),
    "surulere": (6.492, 3.355, "Surulere"),
    "brewery": (6.492, 3.355, "Surulere"),
    "abebe": (6.492, 3.355, "Surulere"),
    "orile": (6.458, 3.345, "Orile / Apapa"),
    "doyin": (6.458, 3.345, "Orile / Apapa"),
    "marina": (6.452, 3.392, "Lagos Island"),
    "outer marina": (6.452, 3.392, "Lagos Island"),
    "train station": (6.452, 3.392, "Lagos Island"),
    "eko bridge": (6.455, 3.385, "Lagos Island / Mainland"),
    "apongbon": (6.455, 3.385, "Lagos Island / Mainland"),
    "victoria island": (6.428, 3.421, "Victoria Island"),
    "bar beach": (6.428, 3.421, "Victoria Island"),
    "bonny camp": (6.428, 3.421, "Victoria Island"),
    "egbeda": (6.595, 3.298, "Egbeda"),
    "oshodi": (6.555, 3.345, "Oshodi"),
    "agbara": (6.508, 3.095, "Agbara / Badagry"),
    "badagry": (6.508, 3.095, "Agbara / Badagry"),
    "ikeja": (6.601, 3.351, "Ikeja"),
    "lekki": (6.447, 3.472, "Lekki"),
    "ajah": (6.469, 3.569, "Ajah"),
    "third mainland": (6.500, 3.390, "Third Mainland Bridge"),
    "carter bridge": (6.455, 3.390, "Lagos Island"),
    "apapa": (6.447, 3.365, "Apapa"),
    "yaba": (6.510, 3.380, "Yaba"),
    "mushin": (6.530, 3.350, "Mushin"),
    "maryland": (6.570, 3.370, "Maryland"),
    "gbagada": (6.550, 3.390, "Gbagada"),
    "berger": (6.620, 3.340, "Berger / Ojodu"),
    "alausa": (6.620, 3.360, "Alausa / Ikeja"),
}


def _guess_location(text: str) -> tuple[str, str, float, float]:
    """Extract a reasonable location name and coordinates from post text."""
    lower = text.lower()
    for key, (lat, lng, area) in LOCATION_COORDS.items():
        if key in lower:
            # Try to build a nicer location string from hashtags or first sentence
            hashtags = re.findall(r"#(\w+)", text)
            loc_parts = [h for h in hashtags if h.lower() not in ("followlastma", "incidentreport", "breakdownreport", "trafficupdate")]
            location = " – ".join(loc_parts[:2]) if loc_parts else key.title()
            return location, area, lat, lng
    # Fallback: centre of Lagos
    return "Lagos (unspecified)", "Lagos", 6.5244, 3.3792


def _classify_type(text: str) -> str:
    lower = text.lower()
    if "breakdown" in lower or "#breakdownreport" in lower:
        return "Breakdown"
    if "incident" in lower or "crash" in lower or "collision" in lower or "#incidentreport" in lower:
        return "Incident"
    if "trafficupdate" in lower or "traffic update" in lower:
        return "Traffic Update"
    return "Report"


def _guess_impact(text: str) -> str:
    lower = text.lower()
    if any(w in lower for w in ("severe", "heavy", "gridlock", "90%", "denied", "blocked")):
        return "Severe"
    if any(w in lower for w in ("moderate", "affecting", "slow")):
        return "Moderate"
    if any(w in lower for w in ("minimal", "less effect", "little effect", "not affecting", "under control")):
        return "Low"
    if "none" in lower or "no effect" in lower:
        return "None"
    return "Unknown"


def _parse_post(tweet: dict) -> dict:
    """Convert a raw X API tweet object into our report schema."""
    text = tweet.get("text", "")
    created = tweet.get("created_at", "")
    tid = tweet.get("id", "")

    # Parse time
    try:
        dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
        time_str = dt.strftime("%H:%M")
        date_str = dt.strftime("%Y-%m-%d")
    except Exception:
        time_str = "—"
        date_str = "—"

    location, area, lat, lng = _guess_location(text)
    rtype = _classify_type(text)
    impact = _guess_impact(text)

    # Clean summary (first 220 chars, no URLs)
    summary = re.sub(r"https?://\S+", "", text).strip()
    summary = re.sub(r"\s+", " ", summary)[:220]
    if len(text) > 220:
        summary += "…"

    has_media = bool(tweet.get("attachments", {}).get("media_keys"))

    return {
        "id": tid,
        "time": time_str,
        "date": date_str,
        "timestamp": created,
        "location": location,
        "area": area,
        "type": rtype,
        "summary": summary,
        "impact": impact,
        "lat": lat,
        "lng": lng,
        "url": f"https://x.com/{X_USERNAME}/status/{tid}",
        "media": has_media,
    }


async def fetch_live_reports() -> list[dict]:
    """
    Fetch recent posts from @followlastma via X API v2 Recent Search.
    Returns a list of normalised report dicts.
    """
    if not X_BEARER_TOKEN:
        raise RuntimeError("X_BEARER_TOKEN is not set")

    query = f"from:{X_USERNAME} -is:retweet -is:reply"
    url = "https://api.x.com/2/tweets/search/recent"
    params = {
        "query": query,
        "max_results": min(MAX_RESULTS, 100),
        "tweet.fields": "created_at,attachments,public_metrics,entities",
        "expansions": "attachments.media_keys",
    }
    headers = {"Authorization": f"Bearer {X_BEARER_TOKEN}"}

    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(url, params=params, headers=headers)
        if resp.status_code == 401:
            raise RuntimeError("Invalid or expired X_BEARER_TOKEN")
        if resp.status_code == 429:
            raise RuntimeError("X API rate limit exceeded – try again later")
        if resp.status_code != 200:
            raise RuntimeError(f"X API error {resp.status_code}: {resp.text[:300]}")

        data = resp.json()
        tweets = data.get("data") or []
        return [_parse_post(t) for t in tweets]


def get_reports_sync() -> tuple[list[dict], str]:
    """
    Synchronous entry point used by the simple HTTP server.
    Returns (reports, source) where source is "live" | "mock" | "cache".
    """
    now = time.time()
    if _cache["data"] is not None and now < _cache["expires"]:
        return _cache["data"], "cache"

    if not X_BEARER_TOKEN:
        return MOCK_REPORTS, "mock"

    # Live fetch (blocking for simplicity with stdlib server)
    try:
        import asyncio
        reports = asyncio.run(fetch_live_reports())
        if not reports:
            # API returned empty – fall back to mock so UI is never blank
            return MOCK_REPORTS, "mock (empty live response)"
        _cache["data"] = reports
        _cache["expires"] = now + CACHE_SECONDS
        return reports, "live"
    except Exception as exc:
        # On any failure return mock + error note
        print(f"[x_client] Live fetch failed: {exc}")
        return MOCK_REPORTS, f"mock (error: {exc})"
