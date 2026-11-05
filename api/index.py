"""Vercel Serverless Function entrypoint for Media Tracker (filmarchive)."""
from http.server import BaseHTTPRequestHandler
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import DEFAULT_DB_FILE, POSTERS_DIR, ensure_schema, make_handler, seed_sample_data  # noqa: E402

ensure_schema(DEFAULT_DB_FILE)
seed_sample_data(DEFAULT_DB_FILE)
POSTERS_DIR.mkdir(parents=True, exist_ok=True)

_GalleryHandler = make_handler(DEFAULT_DB_FILE)


class handler(_GalleryHandler, BaseHTTPRequestHandler):
    """Vercel Python Serverless Function handler."""

    pass
