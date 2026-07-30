"""Configuration for LASTMA Portal backend."""
import os

# X (Twitter) API v2 Bearer Token
# Get one at https://developer.x.com (requires a developer account)
# Free tier is very limited; Basic ($100/mo) or higher needed for reliable recent search.
X_BEARER_TOKEN = os.environ.get("X_BEARER_TOKEN", "").strip()

# Username to follow
X_USERNAME = os.environ.get("X_USERNAME", "followlastma")

# How many posts to fetch (max 100 for recent search on paid tiers)
MAX_RESULTS = int(os.environ.get("MAX_RESULTS", "30"))

# Cache duration in seconds (avoid hitting rate limits)
CACHE_SECONDS = int(os.environ.get("CACHE_SECONDS", "120"))

# Port for the server
PORT = int(os.environ.get("PORT", "8080"))

# Host
HOST = os.environ.get("HOST", "0.0.0.0")
