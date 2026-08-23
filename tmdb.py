#!/usr/bin/env python3
"""TMDB (The Movie Database) API client module.

Uses only stdlib (urllib + json). No pip dependencies required.
API key is read from .env file or TMDB_API_KEY environment variable.
"""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

LOGGER = logging.getLogger("media_tracker.tmdb")

BASE_URL = "https://api.themoviedb.org/3"
IMAGE_BASE = "https://image.tmdb.org/t/p"
DEFAULT_LANGUAGE = "tr-TR"
DEFAULT_POSTER_SIZE = "w500"
REQUEST_DELAY = 0.26  # ~4 req/sec, within TMDB's 40 req/10s limit


def _load_api_key() -> str | None:
    """Load TMDB API key from environment or .env file."""
    key = os.environ.get("TMDB_API_KEY")
    if key:
        return key.strip()
    # Try loading from .env file in project root
    env_path = Path(__file__).resolve().parent / ".env"
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            if k.strip() == "TMDB_API_KEY":
                val = v.strip().strip("\"'")
                if val:
                    os.environ["TMDB_API_KEY"] = val
                    return val
    return None


def get_api_key() -> str:
    """Return the TMDB API key or raise an error."""
    key = _load_api_key()
    if not key:
        raise RuntimeError(
            "TMDB_API_KEY bulunamadı. .env dosyasına TMDB_API_KEY=... ekleyin "
            "veya TMDB_API_KEY environment variable'ı tanımlayın.\n"
            "Ücretsiz anahtar: https://www.themoviedb.org/settings/api"
        )
    return key


def _request(path: str, params: dict[str, str] | None = None) -> dict[str, Any]:
    """Make a GET request to the TMDB API and return parsed JSON."""
    api_key = get_api_key()
    headers = {
        "Accept": "application/json",
        "User-Agent": "MediaTracker/1.0",
    }
    query_params = {}
    if params:
        query_params.update(params)

    # Check if key is a JWT (Bearer Token / API Read Access Token) or standard v3 key (32 hex chars)
    if len(api_key) > 50 or api_key.startswith("eyJ"):
        headers["Authorization"] = f"Bearer {api_key}"
    else:
        query_params["api_key"] = api_key

    query_str = f"?{urllib.parse.urlencode(query_params)}" if query_params else ""
    url = f"{BASE_URL}{path}{query_str}"

    req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        time.sleep(REQUEST_DELAY)
        return data
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        LOGGER.error("TMDB API error %d for %s: %s", e.code, path, body[:200])
        raise
    except urllib.error.URLError as e:
        LOGGER.error("TMDB connection error for %s: %s", path, e.reason)
        raise


# ── Search ──────────────────────────────────────────────────────────


def search_movie(
    query: str,
    year: int | None = None,
    language: str = DEFAULT_LANGUAGE,
    page: int = 1,
) -> dict[str, Any]:
    """Search TMDB for movies by title."""
    params: dict[str, str] = {"query": query, "language": language, "page": str(page)}
    if year:
        params["year"] = str(year)
    return _request("/search/movie", params)


def search_tv(
    query: str,
    year: int | None = None,
    language: str = DEFAULT_LANGUAGE,
    page: int = 1,
) -> dict[str, Any]:
    """Search TMDB for TV series by title."""
    params: dict[str, str] = {"query": query, "language": language, "page": str(page)}
    if year:
        params["first_air_date_year"] = str(year)
    return _request("/search/tv", params)


def search_multi(
    query: str,
    language: str = DEFAULT_LANGUAGE,
    page: int = 1,
) -> dict[str, Any]:
    """Search TMDB for movies and TV series simultaneously."""
    return _request("/search/multi", {"query": query, "language": language, "page": str(page)})


# ── Details ─────────────────────────────────────────────────────────


def get_movie(tmdb_id: int, language: str = DEFAULT_LANGUAGE) -> dict[str, Any]:
    """Fetch full movie details from TMDB."""
    return _request(f"/movie/{tmdb_id}", {"language": language})


def get_tv(tmdb_id: int, language: str = DEFAULT_LANGUAGE) -> dict[str, Any]:
    """Fetch full TV series details from TMDB."""
    return _request(f"/tv/{tmdb_id}", {"language": language})


def get_tv_season(
    tmdb_id: int,
    season_number: int,
    language: str = DEFAULT_LANGUAGE,
) -> dict[str, Any]:
    """Fetch season details for a TV series."""
    return _request(f"/tv/{tmdb_id}/season/{season_number}", {"language": language})


def find_by_imdb(imdb_id: str, language: str = DEFAULT_LANGUAGE) -> dict[str, Any] | None:
    """Find a movie or TV show by its IMDb ID and return localized details."""
    try:
        data = _request(f"/find/{imdb_id}", {"external_source": "imdb_id", "language": language})
        movies = data.get("movie_results", [])
        if movies:
            return movies[0]
        tvs = data.get("tv_results", [])
        if tvs:
            return tvs[0]
    except Exception as e:
        LOGGER.warning("TMDB find_by_imdb failed for %s: %s", imdb_id, e)
    return None


# ── Poster Download ─────────────────────────────────────────────────


def poster_url(poster_path: str, size: str = DEFAULT_POSTER_SIZE) -> str:
    """Construct full poster image URL from TMDB poster path."""
    return f"{IMAGE_BASE}/{size}{poster_path}"


def download_poster(
    poster_path: str,
    dest: Path,
    size: str = DEFAULT_POSTER_SIZE,
    overwrite: bool = False,
) -> bool:
    """Download a poster image to a local file.

    Returns True if the file was downloaded, False if skipped.
    """
    if not poster_path:
        return False
    if dest.is_file() and not overwrite:
        return False

    url = poster_url(poster_path, size)
    req = urllib.request.Request(url, headers={"User-Agent": "MediaTracker/1.0"})

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(resp.read())
        time.sleep(REQUEST_DELAY)
        LOGGER.info("Downloaded poster: %s → %s", poster_path, dest.name)
        return True
    except Exception as e:
        LOGGER.warning("Poster download failed for %s: %s", poster_path, e)
        return False


# ── Data Mapping ────────────────────────────────────────────────────


def movie_to_media(tmdb_data: dict[str, Any]) -> dict[str, Any]:
    """Convert TMDB movie data to Media Tracker record fields."""
    genres = [g["name"] for g in tmdb_data.get("genres", [])]
    release_year = None
    rd = tmdb_data.get("release_date", "")
    if rd and len(rd) >= 4:
        try:
            release_year = int(rd[:4])
        except ValueError:
            pass

    return {
        "title": tmdb_data.get("title") or tmdb_data.get("original_title") or "Untitled",
        "media_type": "movie",
        "is_anime": False,  # Caller should override if needed
        "status": "planned",
        "release_year": release_year,
        "tmdb_id": tmdb_data.get("id"),
        "poster_path": tmdb_data.get("poster_path"),
        "overview": tmdb_data.get("overview"),
        "genres": json.dumps(genres, ensure_ascii=False) if genres else None,
        "original_title": tmdb_data.get("original_title"),
        "runtime": tmdb_data.get("runtime"),
        "tmdb_rating": tmdb_data.get("vote_average"),
    }


def tv_to_media(tmdb_data: dict[str, Any]) -> dict[str, Any]:
    """Convert TMDB TV series data to Media Tracker record fields."""
    genres = [g["name"] for g in tmdb_data.get("genres", [])]
    release_year = None
    fad = tmdb_data.get("first_air_date", "")
    if fad and len(fad) >= 4:
        try:
            release_year = int(fad[:4])
        except ValueError:
            pass

    return {
        "title": tmdb_data.get("name") or tmdb_data.get("original_name") or "Untitled",
        "media_type": "series",
        "is_anime": False,  # Caller should override
        "status": "planned",
        "release_year": release_year,
        "tmdb_id": tmdb_data.get("id"),
        "poster_path": tmdb_data.get("poster_path"),
        "overview": tmdb_data.get("overview"),
        "genres": json.dumps(genres, ensure_ascii=False) if genres else None,
        "original_title": tmdb_data.get("original_name"),
        "runtime": tmdb_data.get("episode_run_time", [None])[0] if tmdb_data.get("episode_run_time") else None,
        "tmdb_rating": tmdb_data.get("vote_average"),
        "seasons": tmdb_data.get("seasons", []),
    }


def search_result_to_summary(item: dict[str, Any]) -> dict[str, Any]:
    """Convert a TMDB search result item to a slim summary for the frontend."""
    media_type = item.get("media_type", "movie")
    if media_type == "tv":
        media_type = "series"

    title = item.get("title") or item.get("name") or "?"
    original = item.get("original_title") or item.get("original_name")
    date_str = item.get("release_date") or item.get("first_air_date") or ""
    year = int(date_str[:4]) if date_str and len(date_str) >= 4 else None

    return {
        "tmdb_id": item.get("id"),
        "title": title,
        "original_title": original,
        "media_type": media_type,
        "release_year": year,
        "poster_path": item.get("poster_path"),
        "overview": (item.get("overview") or "")[:300],
        "tmdb_rating": item.get("vote_average"),
        "poster_preview": poster_url(item["poster_path"], "w185") if item.get("poster_path") else None,
    }
