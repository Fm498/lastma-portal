#!/usr/bin/env python3
"""
LASTMA Traffic Portal – lightweight HTTP backend.

Serves:
  GET /              → frontend (index.html)
  GET /api/reports   → JSON list of traffic reports
  GET /api/health    → health check
  GET /api/stats     → aggregated dashboard stats

Run locally:
  cd backend
  X_BEARER_TOKEN=your_token python main.py

Or without a token (uses rich mock data):
  python main.py
"""
from __future__ import annotations

import json
import mimetypes
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

# Ensure we can import sibling modules
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import HOST, PORT
from x_client import get_reports_sync

# Locate frontend
ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = ROOT / "frontend"
STATIC_DIR = ROOT / "static"


def compute_stats(reports: list[dict]) -> dict:
    total = len(reports)
    breakdowns = sum(1 for r in reports if r.get("type") == "Breakdown")
    incidents = sum(1 for r in reports if r.get("type") == "Incident")
    updates = sum(1 for r in reports if r.get("type") == "Traffic Update")
    areas = len({r.get("area") for r in reports if r.get("area")})
    severe = sum(1 for r in reports if r.get("impact") == "Severe")
    by_area: dict[str, int] = {}
    for r in reports:
        a = r.get("area") or "Unknown"
        by_area[a] = by_area.get(a, 0) + 1
    return {
        "total": total,
        "breakdowns": breakdowns,
        "incidents": incidents,
        "updates": updates,
        "areas": areas,
        "severe": severe,
        "by_area": by_area,
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "LASTMA-Portal/1.0"

    def log_message(self, fmt: str, *args) -> None:
        print(f"[{self.log_date_time_string()}] {fmt % args}")

    def _send_json(self, data: object, status: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path) -> None:
        if not path.is_file():
            self.send_error(404, "File not found")
            return
        ctype, _ = mimetypes.guess_type(str(path))
        ctype = ctype or "application/octet-stream"
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "public, max-age=60")
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        # ---- API ----
        if path == "/api/health":
            self._send_json({"status": "ok", "service": "lastma-portal"})
            return

        if path == "/api/reports":
            reports, source = get_reports_sync()
            self._send_json({
                "source": source,
                "count": len(reports),
                "reports": reports,
            })
            return

        if path == "/api/stats":
            reports, source = get_reports_sync()
            stats = compute_stats(reports)
            stats["source"] = source
            self._send_json(stats)
            return

        # ---- Static / Frontend ----
        if path == "/" or path == "/index.html":
            self._send_file(FRONTEND_DIR / "index.html")
            return

        # Any other static asset under /static/
        if path.startswith("/static/"):
            rel = path[len("/static/"):]
            self._send_file(STATIC_DIR / rel)
            return

        # Fallback: try frontend folder
        candidate = FRONTEND_DIR / path.lstrip("/")
        if candidate.is_file():
            self._send_file(candidate)
            return

        self.send_error(404, f"Not found: {path}")


def main() -> None:
    # Ensure frontend exists
    index = FRONTEND_DIR / "index.html"
    if not index.exists():
        print(f"ERROR: Frontend not found at {index}")
        sys.exit(1)

    token_set = bool(os.environ.get("X_BEARER_TOKEN", "").strip())
    print("=" * 60)
    print("  LASTMA Traffic Portal")
    print("=" * 60)
    print(f"  Listening on  http://{HOST}:{PORT}")
    print(f"  X API mode  : {'LIVE (Bearer token set)' if token_set else 'MOCK (no X_BEARER_TOKEN)'}")
    print(f"  Frontend    : {FRONTEND_DIR}")
    print("=" * 60)
    print("  Endpoints:")
    print(f"    GET /              → UI")
    print(f"    GET /api/reports   → traffic reports JSON")
    print(f"    GET /api/stats     → dashboard stats")
    print(f"    GET /api/health    → health check")
    print("=" * 60)

    server = ThreadingHTTPServer((HOST, PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down…")
        server.shutdown()


if __name__ == "__main__":
    main()
