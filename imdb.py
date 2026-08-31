#!/usr/bin/env python3
"""Media Tracker IMDb client compatibility shim pointing to unified app.py."""
from app import (
    imdb_search as search_imdb,
    imdb_get_details as get_imdb_details,
    imdb_get_random_top as get_random_imdb_top,
    imdb_download_poster as download_poster,
)
