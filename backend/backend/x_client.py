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
    # ---- Late July 2026 ----
    {"id": "2082736716385783909", "time": "08:48", "date": "2026-07-30", "timestamp": "2026-07-30T07:55:03Z",
     "location": "Agege Motor Rd – Airport Bus Stop", "area": "Agege / Ikeja", "type": "Breakdown",
     "summary": "Broken down 22-tyre truck at Airport Bus stop inward National Flyover. Cones placed, recovery in progress.",
     "impact": "Minimal", "lat": 6.585, "lng": 3.338, "url": "https://x.com/followlastma/status/2082736716385783909", "media": True},
    {"id": "2082721420723843230", "time": "07:50", "date": "2026-07-30", "timestamp": "2026-07-30T06:54:16Z",
     "location": "Ikorodu – Okegbegun", "area": "Ikorodu", "type": "Incident",
     "summary": "Flat-body truck spilled contents + 40ft container truck brake failure collision. ~90% access denied.",
     "impact": "Severe", "lat": 6.615, "lng": 3.505, "url": "https://x.com/followlastma/status/2082721420723843230", "media": True},
    {"id": "2082719629546307962", "time": "07:35", "date": "2026-07-30", "timestamp": "2026-07-30T06:47:09Z",
     "location": "Surulere – Abebe Village / Brewery", "area": "Surulere", "type": "Breakdown",
     "summary": "Loaded containerized truck rear tyre problem at Abebe Village by Brewery inward Eric Moore.",
     "impact": "Controlled", "lat": 6.492, "lng": 3.355, "url": "https://x.com/followlastma/status/2082719629546307962", "media": True},
    {"id": "2082711814601601185", "time": "07:10", "date": "2026-07-30", "timestamp": "2026-07-30T06:16:06Z",
     "location": "Orile – Doyin", "area": "Orile / Apapa", "type": "Incident",
     "summary": "20ft containerized truck stuck on BRT demarcation at Doyin inward Orile. Tow vehicle on ground.",
     "impact": "Low", "lat": 6.458, "lng": 3.345, "url": "https://x.com/followlastma/status/2082711814601601185", "media": True},
    {"id": "2082699145731523023", "time": "06:06", "date": "2026-07-30", "timestamp": "2026-07-30T05:25:45Z",
     "location": "Outer Marina – Train Station", "area": "Lagos Island", "type": "Incident",
     "summary": "Mack flatbed loaded with iron rods hooked on BRT median by Train Station, Marina.",
     "impact": "Low", "lat": 6.452, "lng": 3.392, "url": "https://x.com/followlastma/status/2082699145731523023", "media": True},
    {"id": "2082681084630741144", "time": "04:56", "date": "2026-07-30", "timestamp": "2026-07-30T04:13:59Z",
     "location": "Eko Bridge inward Apongbon", "area": "Lagos Island / Mainland", "type": "Breakdown",
     "summary": "Loaded 20ft container truck broken spring on Eko Bridge. On-spot repair ongoing.",
     "impact": "Moderate", "lat": 6.455, "lng": 3.385, "url": "https://x.com/followlastma/status/2082681084630741144", "media": True},
    {"id": "2082494369932738737", "time": "16:40", "date": "2026-07-29", "timestamp": "2026-07-29T15:52:03Z",
     "location": "Victoria Island – Bar Beach / Bonny Camp", "area": "Victoria Island", "type": "Incident",
     "summary": "Road crash involving two flat-bed trucks at Bar-Beach front inward Bonny Camp.",
     "impact": "Low", "lat": 6.428, "lng": 3.421, "url": "https://x.com/followlastma/status/2082494369932738737", "media": True},
    {"id": "2082488536226209859", "time": "16:25", "date": "2026-07-29", "timestamp": "2026-07-29T15:28:52Z",
     "location": "Egbeda – Baale / Oniwaya", "area": "Egbeda", "type": "Incident",
     "summary": "Mini truck stuck in drainage while reversing to offload at Baale inward Oniwaya.",
     "impact": "Moderate", "lat": 6.595, "lng": 3.298, "url": "https://x.com/followlastma/status/2082488536226209859", "media": True},
    {"id": "2082487299766415774", "time": "16:18", "date": "2026-07-29", "timestamp": "2026-07-29T15:23:57Z",
     "location": "Oshodi Bridge inward Anthony", "area": "Oshodi", "type": "Breakdown",
     "summary": "Loaded truck broke down ascending Oshodi Bridge inward Anthony. One lane taken.",
     "impact": "Moderate", "lat": 6.555, "lng": 3.345, "url": "https://x.com/followlastma/status/2082487299766415774", "media": True},
    {"id": "2082479040611430722", "time": "15:47", "date": "2026-07-29", "timestamp": "2026-07-29T14:51:08Z",
     "location": "Agbara Car Wash – Lagos-Badagry Exp Way", "area": "Agbara / Badagry", "type": "Breakdown",
     "summary": "Loaded Mack containerized truck mechanical fault at Agbara Car Wash inward Badagry.",
     "impact": "None", "lat": 6.508, "lng": 3.095, "url": "https://x.com/followlastma/status/2082479040611430722", "media": True},
    # ---- Mid-late July ----
    {"id": "2080992656709030197", "time": "13:20", "date": "2026-07-25", "timestamp": "2026-07-25T12:24:46Z",
     "location": "NNPC Intersection", "area": "Ejigbo / Isolo", "type": "Breakdown",
     "summary": "MAN tanker broken down at NNPC Intersection due to clutch fault, obstructing traffic inward Iyana-Ejigbo.",
     "impact": "Moderate", "lat": 6.551, "lng": 3.312, "url": "https://x.com/followlastma/status/2080992656709030197", "media": True},
    {"id": "2080628967560593726", "time": "08:15", "date": "2026-07-24", "timestamp": "2026-07-24T07:15:00Z",
     "location": "Kara Bridge – Lagos-Ibadan Expressway", "area": "Berger / Ojodu", "type": "Incident",
     "summary": "Multiple-vehicle collision on Kara Bridge inward Mowe-Ibafo. Motor boy fatality. Severe gridlock.",
     "impact": "Severe", "lat": 6.620, "lng": 3.340, "url": "https://x.com/followlastma/status/2080628967560593726", "media": False},
    {"id": "2079910941219545266", "time": "11:30", "date": "2026-07-22", "timestamp": "2026-07-22T10:30:00Z",
     "location": "LASU–Isheri Road – Iyana School", "area": "Igando", "type": "Incident",
     "summary": "MACK flatbed brake failure collision with Sienna and tricycles at Iyana School inward Igando. 3 victims rescued.",
     "impact": "Severe", "lat": 6.548, "lng": 3.255, "url": "https://x.com/followlastma/status/2079910941219545266", "media": False},
    {"id": "2079500000000000001", "time": "09:10", "date": "2026-07-21", "timestamp": "2026-07-21T08:10:00Z",
     "location": "Third Mainland Bridge – Adekunle", "area": "Lagos Island / Mainland", "type": "Traffic Update",
     "summary": "Traffic flowing smoothly from Adekunle through Adeniji Adele to Sura Junction. No major impediments.",
     "impact": "None", "lat": 6.500, "lng": 3.390, "url": "https://x.com/followlastma/status/2079500000000000001", "media": False},
    {"id": "2079200000000000002", "time": "17:45", "date": "2026-07-20", "timestamp": "2026-07-20T16:45:00Z",
     "location": "Lekki–Epe Expressway – Sangotedo", "area": "Lekki / Ajah", "type": "Traffic Update",
     "summary": "Movement from Ilaje to Ajah, Abraham Adesanya and LBS currently clear and moving well.",
     "impact": "None", "lat": 6.447, "lng": 3.520, "url": "https://x.com/followlastma/status/2079200000000000002", "media": False},
    {"id": "2078900000000000003", "time": "07:20", "date": "2026-07-19", "timestamp": "2026-07-19T06:20:00Z",
     "location": "Apapa–Oshodi Expressway – Mile 2", "area": "Apapa / Oshodi", "type": "Breakdown",
     "summary": "Articulated tanker with brake issues at Mile 2 inward Oshodi. Recovery team mobilised.",
     "impact": "Moderate", "lat": 6.455, "lng": 3.320, "url": "https://x.com/followlastma/status/2078900000000000003", "media": True},
    {"id": "2078600000000000004", "time": "14:05", "date": "2026-07-18", "timestamp": "2026-07-18T13:05:00Z",
     "location": "Ikeja – Allen Avenue / Opebi", "area": "Ikeja", "type": "Incident",
     "summary": "Minor collision involving two private cars at Allen junction. One lane partially blocked.",
     "impact": "Low", "lat": 6.601, "lng": 3.351, "url": "https://x.com/followlastma/status/2078600000000000004", "media": False},
    {"id": "2078300000000000005", "time": "08:40", "date": "2026-07-17", "timestamp": "2026-07-17T07:40:00Z",
     "location": "Gbagada – Olopomeji Bridge", "area": "Gbagada", "type": "Incident",
     "summary": "Overturned loaded truck at TREM Church inward Gbagada. Traffic diverted to service lane.",
     "impact": "Severe", "lat": 6.550, "lng": 3.390, "url": "https://x.com/followlastma/status/2078300000000000005", "media": True},
    {"id": "2078000000000000006", "time": "16:30", "date": "2026-07-16", "timestamp": "2026-07-16T15:30:00Z",
     "location": "Maryland – Mobolaji Bank Anthony Way", "area": "Maryland", "type": "Traffic Update",
     "summary": "Traffic good from Ikeja under-bridge through Maryland to Anthony. Officers on ground.",
     "impact": "None", "lat": 6.570, "lng": 3.370, "url": "https://x.com/followlastma/status/2078000000000000006", "media": False},
    {"id": "2077700000000000007", "time": "06:55", "date": "2026-07-15", "timestamp": "2026-07-15T05:55:00Z",
     "location": "Badagry Expressway – Trade Fair", "area": "Agbara / Badagry", "type": "Breakdown",
     "summary": "Loaded container truck mechanical fault near Trade Fair Complex inward Badagry.",
     "impact": "Low", "lat": 6.470, "lng": 3.180, "url": "https://x.com/followlastma/status/2077700000000000007", "media": True},
    # ---- Mid July ----
    {"id": "2077400000000000008", "time": "12:15", "date": "2026-07-14", "timestamp": "2026-07-14T11:15:00Z",
     "location": "Yaba – University Road", "area": "Yaba", "type": "Incident",
     "summary": "Commercial bus collided with motorcycle near Unilag gate. Casualties treated on site.",
     "impact": "Moderate", "lat": 6.510, "lng": 3.380, "url": "https://x.com/followlastma/status/2077400000000000008", "media": False},
    {"id": "2077100000000000009", "time": "09:00", "date": "2026-07-13", "timestamp": "2026-07-13T08:00:00Z",
     "location": "Alausa – Obafemi Awolowo Way", "area": "Alausa / Ikeja", "type": "Traffic Update",
     "summary": "Smooth flow from Barrack through Coca-Cola, Allen, Balogun to Ikeja under-bridge.",
     "impact": "None", "lat": 6.620, "lng": 3.360, "url": "https://x.com/followlastma/status/2077100000000000009", "media": False},
    {"id": "2076800000000000010", "time": "18:20", "date": "2026-07-12", "timestamp": "2026-07-12T17:20:00Z",
     "location": "Lekki Phase 1 – Admiralty Way", "area": "Lekki", "type": "Breakdown",
     "summary": "Private SUV with flat tyre obstructing one lane on Admiralty Way. Being attended to.",
     "impact": "Low", "lat": 6.447, "lng": 3.472, "url": "https://x.com/followlastma/status/2076800000000000010", "media": False},
    {"id": "2076500000000000011", "time": "07:45", "date": "2026-07-11", "timestamp": "2026-07-11T06:45:00Z",
     "location": "Mushin – Agege Motor Road", "area": "Mushin", "type": "Incident",
     "summary": "Hit-and-run involving a tanker and delivery rider on Kodesho Road, Ikeja axis. Driver later apprehended.",
     "impact": "Severe", "lat": 6.530, "lng": 3.350, "url": "https://x.com/followlastma/status/2076500000000000011", "media": False},
    {"id": "2076200000000000012", "time": "15:10", "date": "2026-07-10", "timestamp": "2026-07-10T14:10:00Z",
     "location": "CMS – Outer Marina", "area": "Lagos Island", "type": "Traffic Update",
     "summary": "Favourable traffic ascending Obalende Bridge through Osborne, Simpson Bridge to Ilubirin.",
     "impact": "None", "lat": 6.450, "lng": 3.395, "url": "https://x.com/followlastma/status/2076200000000000012", "media": False},
    {"id": "2075900000000000013", "time": "08:25", "date": "2026-07-09", "timestamp": "2026-07-09T07:25:00Z",
     "location": "Berger – Kara Bridge", "area": "Berger / Ojodu", "type": "Incident",
     "summary": "Fully-laden articulated vehicle veered off carriageway near Kara Bridge crest. Significant congestion.",
     "impact": "Severe", "lat": 6.620, "lng": 3.340, "url": "https://x.com/followlastma/status/2075900000000000013", "media": True},
    {"id": "2075600000000000014", "time": "11:50", "date": "2026-07-08", "timestamp": "2026-07-08T10:50:00Z",
     "location": "Ajah – Abraham Adesanya", "area": "Lekki / Ajah", "type": "Breakdown",
     "summary": "Tipper truck with engine failure at Abraham Adesanya junction. Recovery in progress.",
     "impact": "Moderate", "lat": 6.469, "lng": 3.569, "url": "https://x.com/followlastma/status/2075600000000000014", "media": True},
    {"id": "2075300000000000015", "time": "17:00", "date": "2026-07-07", "timestamp": "2026-07-07T16:00:00Z",
     "location": "Oshodi – Bolade Intersection", "area": "Oshodi", "type": "Traffic Update",
     "summary": "Traffic good leaving Oshodi through Brown intersection, Bolade, Ladipo to Airport area.",
     "impact": "None", "lat": 6.555, "lng": 3.335, "url": "https://x.com/followlastma/status/2075300000000000015", "media": False},
    # ---- Early July ----
    {"id": "2075000000000000016", "time": "06:30", "date": "2026-07-06", "timestamp": "2026-07-06T05:30:00Z",
     "location": "Ikorodu Road – Mile 12", "area": "Ikorodu", "type": "Incident",
     "summary": "Multiple vehicle pile-up near Mile 12 market entrance. Two lanes affected.",
     "impact": "Severe", "lat": 6.605, "lng": 3.400, "url": "https://x.com/followlastma/status/2075000000000000016", "media": True},
    {"id": "2074700000000000017", "time": "13:40", "date": "2026-07-05", "timestamp": "2026-07-05T12:40:00Z",
     "location": "Victoria Island – Ahmadu Bello Way", "area": "Victoria Island", "type": "Breakdown",
     "summary": "Luxury bus with transmission fault near Eko Hotel. Minimal traffic impact.",
     "impact": "Low", "lat": 6.430, "lng": 3.420, "url": "https://x.com/followlastma/status/2074700000000000017", "media": False},
    {"id": "2074400000000000018", "time": "09:15", "date": "2026-07-04", "timestamp": "2026-07-04T08:15:00Z",
     "location": "Surulere – National Stadium", "area": "Surulere", "type": "Traffic Update",
     "summary": "Free flow around National Stadium corridor and Eric Moore axis this morning.",
     "impact": "None", "lat": 6.495, "lng": 3.360, "url": "https://x.com/followlastma/status/2074400000000000018", "media": False},
    {"id": "2074100000000000019", "time": "16:50", "date": "2026-07-03", "timestamp": "2026-07-03T15:50:00Z",
     "location": "Agege Motor Road – Oshodi to Ikeja", "area": "Agege / Ikeja", "type": "Traffic Update",
     "summary": "Traffic good leaving Oshodi through Bolade, Ladipo, Shogunle to Airport and National.",
     "impact": "None", "lat": 6.580, "lng": 3.340, "url": "https://x.com/followlastma/status/2074100000000000019", "media": True},
    {"id": "2073800000000000020", "time": "07:05", "date": "2026-07-02", "timestamp": "2026-07-02T06:05:00Z",
     "location": "Apapa Port Access – Wharf Road", "area": "Apapa", "type": "Incident",
     "summary": "Container truck jackknifed near port gate. Heavy congestion on Apapa access roads.",
     "impact": "Severe", "lat": 6.447, "lng": 3.365, "url": "https://x.com/followlastma/status/2073800000000000020", "media": True},
    {"id": "2073500000000000021", "time": "10:30", "date": "2026-07-01", "timestamp": "2026-07-01T09:30:00Z",
     "location": "Ikeja – Computer Village axis", "area": "Ikeja", "type": "Breakdown",
     "summary": "Commercial bus engine failure near Computer Village. Officers managing traffic.",
     "impact": "Low", "lat": 6.595, "lng": 3.345, "url": "https://x.com/followlastma/status/2073500000000000021", "media": False},
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
    Reports are sorted newest-first by date/time.
    """
    def _sort(reports: list[dict]) -> list[dict]:
        return sorted(
            reports,
            key=lambda r: (r.get("date", ""), r.get("time", "")),
            reverse=True,
        )

    now = time.time()
    if _cache["data"] is not None and now < _cache["expires"]:
        return _cache["data"], "cache"

    if not X_BEARER_TOKEN:
        return _sort(MOCK_REPORTS), "mock"

    # Live fetch (blocking for simplicity with stdlib server)
    try:
        import asyncio
        reports = asyncio.run(fetch_live_reports())
        if not reports:
            # API returned empty – fall back to mock so UI is never blank
            return _sort(MOCK_REPORTS), "mock (empty live response)"
        reports = _sort(reports)
        _cache["data"] = reports
        _cache["expires"] = now + CACHE_SECONDS
        return reports, "live"
    except Exception as exc:
        # On any failure return mock + error note
        print(f"[x_client] Live fetch failed: {exc}")
        return _sort(MOCK_REPORTS), f"mock (error: {exc})"
