#!/usr/bin/env python3
"""IMDb data client module — 100% Free, Zero API Key required.

Uses:
1. IMDb official suggestion API (https://v3.sg.media-imdb.com/suggestion) for instant search
2. Cinemeta metadata API (https://v3-cinemeta.strem.io) for full movie/series details & seasons
3. High-resolution Amazon/IMDb CDN posters

No pip dependencies required (pure stdlib urllib + json).
"""

from __future__ import annotations

import json
import logging
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

LOGGER = logging.getLogger("media_tracker.imdb")

IMDB_SUGGESTION_URL = "https://v3.sg.media-imdb.com/suggestion"
CINEMETA_URL = "https://v3-cinemeta.strem.io/meta"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"


def _slugify_search(query: str) -> str:
    """Prepare a search query for IMDb suggestion endpoint."""
    q = query.lower().strip()
    q = re.sub(r"[^a-z0-9_ -]", "", q)
    q = re.sub(r"[\s-]+", "_", q)
    return q if q else "a"


def search_imdb(query: str) -> list[dict[str, Any]]:
    """Search IMDb for movies and TV series without any API key."""
    clean_q = _slugify_search(query)
    if not clean_q:
        return []
    first_char = clean_q[0]
    url = f"{IMDB_SUGGESTION_URL}/{first_char}/{clean_q}.json"

    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        LOGGER.warning("IMDb suggestion search error for '%s': %s", query, e)
        return []

    results = []
    items = data.get("d", [])
    for item in items:
        imdb_id = item.get("id", "")
        if not imdb_id.startswith("tt"):
            continue  # Skip actor/person results (nm...)

        q_type = (item.get("q") or item.get("qid") or "").lower()
        media_type = "series" if "tv" in q_type or "series" in q_type else "movie"

        img_obj = item.get("i")
        poster_url = img_obj.get("imageUrl") if isinstance(img_obj, dict) else None

        results.append({
            "imdb_id": imdb_id,
            "title": item.get("l") or "Untitled",
            "original_title": item.get("l"),
            "release_year": item.get("y"),
            "media_type": media_type,
            "stars": item.get("s") or "",
            "poster_url": poster_url,
            "rank": item.get("rank"),
        })

    return results


def get_imdb_details(imdb_id: str, media_type: str = "movie") -> dict[str, Any]:
    """Fetch full metadata for a movie or TV series via Cinemeta."""
    cinemeta_type = "series" if media_type == "series" else "movie"
    url = f"{CINEMETA_URL}/{cinemeta_type}/{imdb_id}.json"

    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        LOGGER.warning("Cinemeta metadata fetch failed for %s: %s", imdb_id, e)
        # Fallback to alternative type
        alt_type = "series" if cinemeta_type == "movie" else "movie"
        try:
            alt_url = f"{CINEMETA_URL}/{alt_type}/{imdb_id}.json"
            req = urllib.request.Request(alt_url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception:
            return {}

    meta = data.get("meta", {})
    if not meta:
        return {}

    # Extract year
    year = None
    year_raw = meta.get("year") or meta.get("releaseInfo")
    if year_raw:
        m = re.search(r"\b(19\d\d|20\d\d)\b", str(year_raw))
        if m:
            year = int(m.group(1))

    # Extract rating
    rating = None
    rating_raw = meta.get("imdbRating")
    if rating_raw:
        try:
            rating = float(rating_raw)
        except (ValueError, TypeError):
            pass

    # Extract runtime
    runtime = None
    rt_raw = meta.get("runtime")
    if rt_raw:
        m = re.search(r"(\d+)", str(rt_raw))
        if m:
            runtime = int(m.group(1))

    # Extract genres
    genres = meta.get("genre") or meta.get("genres") or []
    if isinstance(genres, str):
        genres = [g.strip() for g in genres.split(",")]

    # Extract director and cast
    director = meta.get("director") or []
    if isinstance(director, list):
        director = ", ".join(director)
    cast = meta.get("cast") or []
    if isinstance(cast, list):
        cast = ", ".join(cast[:5])

    # Extract seasons if series
    seasons = []
    videos = meta.get("videos", [])
    if videos:
        season_counts: dict[int, int] = {}
        for v in videos:
            s_num = v.get("season", 0)
            if s_num > 0:
                season_counts[s_num] = season_counts.get(s_num, 0) + 1
        for sn in sorted(season_counts.keys()):
            seasons.append({"season_number": sn, "episode_count": season_counts[sn]})

    return {
        "imdb_id": imdb_id,
        "title": meta.get("name") or meta.get("title") or "Untitled",
        "original_title": meta.get("name") or meta.get("title"),
        "media_type": "series" if meta.get("type") == "series" else "movie",
        "release_year": year,
        "imdb_rating": rating,
        "overview": meta.get("description"),
        "genres": json.dumps(genres, ensure_ascii=False) if genres else None,
        "director": director or None,
        "cast": cast or None,
        "runtime": runtime,
        "poster_url": meta.get("poster"),
        "seasons": seasons,
    }


def get_random_imdb_top() -> dict[str, Any] | None:
    """Get a random classic / top movie from IMDb."""
    import random
    top_queries = [
        "godfather", "shawshank", "dark_knight", "pulp_fiction", "inception",
        "matrix", "interstellar", "fight_club", "spirited_away", "se7en",
        "forrest_gump", "goodfellas", "gladiator", "oppenheimer", "blade_runner",
        "alien", "psycho", "casablanca", "whiplash", "parasite", "spider_man"
    ]
    query = random.choice(top_queries)
    results = search_imdb(query)
    if results:
        best = results[0]
        # Fetch metadata
        details = get_imdb_details(best["imdb_id"], best["media_type"])
        return details if details else best
    return None


def download_poster(image_url: str, dest: Path, overwrite: bool = False) -> bool:
    """Download a poster image from a direct URL to a local destination."""
    if not image_url:
        return False
    if dest.is_file() and not overwrite:
        return False

    req = urllib.request.Request(image_url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(resp.read())
        LOGGER.info("Downloaded poster: %s -> %s", image_url[:60], dest.name)
        return True
    except Exception as e:
        LOGGER.warning("Poster download failed from %s: %s", image_url[:60], e)
        return False
