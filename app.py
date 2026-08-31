#!/usr/bin/env python3
"""Media Tracker — Standalone Unified Application (Server, API, CLI, TMDB & IMDb).

Pure Python standard library + SQLite. Zero external pip dependencies.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import logging
import mimetypes
import os
import random
import re
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

# Ensure UTF-8 standard output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent
SCHEMA_FILE = ROOT / "schema.sql"
DEFAULT_DB_FILE = ROOT / "data" / "media.sqlite" if (ROOT / "data" / "media.sqlite").is_file() else ROOT / "media.sqlite"
TEMPLATE_PATH = ROOT / "templates" / "gallery.html" if (ROOT / "templates" / "gallery.html").is_file() else ROOT / "gallery.html"
STATIC_DIR = ROOT / "static"
POSTERS_DIR = STATIC_DIR / "posters"
STATIC_URL_PREFIX = "/static/"
POSTERS_URL_PREFIX = "/static/posters/"

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8766
DEFAULT_LIMIT = 50
MAX_LIMIT = 200
SERVER_VERSION = "MediaTracker/5.0"
INTERNAL_ERROR_MESSAGE = "İstek işlenirken bir hata oluştu."
SCHEMA_VERSION = 6

LOGGER = logging.getLogger("media_tracker")

STATUSES = ("planned", "in_progress", "completed", "paused", "dropped")
MEDIA_TYPES = ("movie", "series", "book")
GALLERY_FILTERS = ("all", "movie", "anime-movie", "series", "anime-series", "anime")
GALLERY_KINDS_SQL_EXCLUDE_BOOK = "m.media_type != 'book'"

SORT_COLUMNS = {
    "updated_at": "m.updated_at",
    "created_at": "m.created_at",
    "title": "m.title",
    "rating": "m.rating",
    "release_year": "m.release_year",
    "status": "m.status",
    "id": "m.id",
}

# ── TMDB & IMDb CONFIG ───────────────────────────────────────────────
TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p"
TMDB_DEFAULT_LANG = "tr-TR"
TMDB_DEFAULT_POSTER_SIZE = "w500"
TMDB_REQUEST_DELAY = 0.25

IMDB_SUGGESTION_URL = "https://v3.sg.media-imdb.com/suggestion"
CINEMETA_URL = "https://v3-cinemeta.strem.io/meta"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

# Embedded Base SQL Schema fallback
BASE_SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS media (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL CHECK (trim(title) <> ''),
    media_type TEXT NOT NULL CHECK (media_type IN ('book', 'movie', 'series')),
    is_anime INTEGER NOT NULL DEFAULT 0 CHECK (is_anime IN (0, 1)),
    status TEXT NOT NULL DEFAULT 'planned'
        CHECK (status IN ('planned', 'in_progress', 'completed', 'paused', 'dropped')),
    release_year INTEGER
        CHECK (release_year IS NULL OR release_year BETWEEN 1800 AND 2100),
    rating INTEGER CHECK (rating IS NULL OR rating BETWEEN 1 AND 10),
    note TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (media_type <> 'book' OR is_anime = 0)
);

CREATE TABLE IF NOT EXISTS book_details (
    media_id INTEGER PRIMARY KEY,
    author TEXT NOT NULL CHECK (trim(author) <> ''),
    total_pages INTEGER CHECK (total_pages IS NULL OR total_pages > 0),
    read_pages INTEGER NOT NULL DEFAULT 0 CHECK (read_pages >= 0),
    FOREIGN KEY (media_id) REFERENCES media(id) ON DELETE CASCADE,
    CHECK (total_pages IS NULL OR read_pages <= total_pages)
);

CREATE TABLE IF NOT EXISTS series_seasons (
    media_id INTEGER NOT NULL,
    season_number INTEGER NOT NULL CHECK (season_number > 0),
    episode_count INTEGER CHECK (episode_count IS NULL OR episode_count > 0),
    watched_episodes INTEGER NOT NULL DEFAULT 0 CHECK (watched_episodes >= 0),
    PRIMARY KEY (media_id, season_number),
    FOREIGN KEY (media_id) REFERENCES media(id) ON DELETE CASCADE,
    CHECK (episode_count IS NULL OR watched_episodes <= episode_count)
);

CREATE INDEX IF NOT EXISTS idx_media_title ON media(title COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_media_type_anime ON media(media_type, is_anime);
CREATE INDEX IF NOT EXISTS idx_media_status ON media(status);
CREATE INDEX IF NOT EXISTS idx_media_rating ON media(rating);
CREATE INDEX IF NOT EXISTS idx_media_updated_at ON media(updated_at);
CREATE INDEX IF NOT EXISTS idx_series_seasons_media ON series_seasons(media_id, season_number);

CREATE TRIGGER IF NOT EXISTS trg_media_updated_at
AFTER UPDATE ON media
FOR EACH ROW
WHEN NEW.updated_at = OLD.updated_at
BEGIN
    UPDATE media SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

PRAGMA user_version = 2;
"""


# =====================================================================
# 1. DATABASE & MODEL LAYER
# =====================================================================

def make_db_path(path_str: str | None = None) -> Path:
    """Return the resolved Path to the SQLite database."""
    if path_str:
        return Path(path_str).resolve()
    data_db = ROOT / "data" / "media.sqlite"
    if data_db.is_file():
        return data_db
    if (ROOT / "media.sqlite").is_file():
        return ROOT / "media.sqlite"
    (ROOT / "data").mkdir(parents=True, exist_ok=True)
    return data_db


def connect(db_path: Path) -> sqlite3.Connection:
    """Establish and configure a SQLite connection."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _migrate_columns(conn: sqlite3.Connection) -> None:
    """Apply schema migration — ensure all extra columns and indices exist."""
    new_columns = [
        ("tmdb_id", "INTEGER"),
        ("imdb_id", "TEXT"),
        ("poster_path", "TEXT"),
        ("overview", "TEXT"),
        ("genres", "TEXT"),
        ("original_title", "TEXT"),
        ("director", "TEXT"),
        ("cast_members", "TEXT"),
        ("runtime", "INTEGER"),
        ("tmdb_rating", "REAL"),
        ("imdb_rating", "REAL"),
        ("tags", "TEXT"),
        ("trailer_key", "TEXT"),
        ("watched_at", "TEXT"),
        ("times_watched", "INTEGER DEFAULT 1"),
        ("is_favorite", "INTEGER DEFAULT 0"),
    ]
    existing = {row[1] for row in conn.execute("PRAGMA table_info(media)").fetchall()}
    for col_name, col_type in new_columns:
        if col_name not in existing:
            conn.execute(f"ALTER TABLE media ADD COLUMN {col_name} {col_type}")

    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_media_tmdb_id ON media(tmdb_id) WHERE tmdb_id IS NOT NULL")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_media_imdb_id ON media(imdb_id) WHERE imdb_id IS NOT NULL")
    conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    conn.commit()


def ensure_schema(db_path: Path) -> None:
    """Ensure that the database schema is applied and up to date."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        version_row = conn.execute("PRAGMA user_version").fetchone()
        version = int(version_row[0]) if version_row else 0
        if version == 0:
            if SCHEMA_FILE.is_file():
                schema_sql = SCHEMA_FILE.read_text(encoding="utf-8")
            else:
                schema_sql = BASE_SCHEMA_SQL
            conn.executescript(schema_sql)
            _migrate_columns(conn)
        else:
            _migrate_columns(conn)
    finally:
        conn.close()


def media_where(
    kind: str = "all",
    query: str = "",
    status: str | None = None,
    tag: str | None = None,
    min_rating: float | None = None,
    min_year: int | None = None,
    max_year: int | None = None,
    max_runtime: int | None = None,
    is_favorite: bool | None = None,
) -> tuple[str, list[Any]]:
    """Construct SQL WHERE clause and parameter list based on filter criteria."""
    clauses: list[str] = []
    values: list[Any] = []

    if kind == "movie":
        clauses.append("m.media_type = 'movie' AND m.is_anime = 0")
    elif kind == "anime-movie":
        clauses.append("m.media_type = 'movie' AND m.is_anime = 1")
    elif kind == "series":
        clauses.append("m.media_type = 'series' AND m.is_anime = 0")
    elif kind == "anime-series":
        clauses.append("m.media_type = 'series' AND m.is_anime = 1")
    elif kind == "anime":
        clauses.append("m.is_anime = 1")
    elif kind == "book":
        clauses.append("m.media_type = 'book'")

    if status and status in STATUSES:
        clauses.append("m.status = ?")
        values.append(status)

    if tag:
        clauses.append("m.tags LIKE ?")
        values.append(f"%{tag}%")

    if is_favorite:
        clauses.append("m.is_favorite = 1")

    if min_rating is not None and min_rating > 0:
        clauses.append("COALESCE(m.rating, m.imdb_rating, m.tmdb_rating) >= ?")
        values.append(min_rating)

    if min_year is not None and min_year > 0:
        clauses.append("m.release_year >= ?")
        values.append(min_year)

    if max_year is not None and max_year > 0:
        clauses.append("m.release_year <= ?")
        values.append(max_year)

    if max_runtime is not None and max_runtime > 0:
        clauses.append("m.runtime <= ?")
        values.append(max_runtime)

    if query:
        clauses.append("(m.title LIKE ? OR m.original_title LIKE ? OR m.note LIKE ? OR CAST(m.release_year AS TEXT) LIKE ? OR m.director LIKE ? OR m.cast_members LIKE ?)")
        q_like = f"%{query}%"
        values.extend([q_like, q_like, q_like, q_like, q_like, q_like])

    where = "WHERE " + " AND ".join(clauses) if clauses else ""
    return where, values


def base_record_sql() -> str:
    """Return base SELECT query for media records with joined book and series details."""
    return """
        SELECT
            m.id,
            m.title,
            m.media_type,
            m.is_anime,
            m.status,
            m.release_year,
            m.rating,
            m.note,
            m.created_at,
            m.updated_at,
            m.tmdb_id,
            m.imdb_id,
            m.poster_path,
            m.overview,
            m.genres,
            m.original_title,
            m.director,
            m.cast_members,
            m.runtime,
            m.tmdb_rating,
            m.imdb_rating,
            m.tags,
            m.trailer_key,
            m.watched_at,
            m.times_watched,
            m.is_favorite,
            bd.author,
            bd.total_pages,
            bd.read_pages,
            COALESCE(SUM(ss.watched_episodes), 0) AS watched_episodes,
            SUM(ss.episode_count) AS total_episodes,
            COUNT(ss.season_number) AS season_count
        FROM media AS m
        LEFT JOIN book_details AS bd ON bd.media_id = m.id
        LEFT JOIN series_seasons AS ss ON ss.media_id = m.id
    """


def row_to_record(row: sqlite3.Row) -> dict[str, Any]:
    """Convert a sqlite3.Row to a standard dictionary with proper typing."""
    d = dict(row)
    d["is_anime"] = bool(d.get("is_anime", 0))
    genres_raw = d.get("genres")
    if genres_raw and isinstance(genres_raw, str):
        try:
            d["genres"] = json.loads(genres_raw)
        except (json.JSONDecodeError, ValueError):
            d["genres"] = [g.strip() for g in genres_raw.split(",") if g.strip()]
    elif not genres_raw:
        d["genres"] = []

    tags_raw = d.get("tags")
    if tags_raw and isinstance(tags_raw, str):
        try:
            d["tags"] = json.loads(tags_raw)
        except (json.JSONDecodeError, ValueError):
            d["tags"] = [t.strip() for t in tags_raw.split(",") if t.strip()]
    elif not tags_raw:
        d["tags"] = []

    return d


def fetch_media(conn: sqlite3.Connection, media_id: int, include_seasons: bool = True) -> dict[str, Any] | None:
    """Fetch a single media record by ID with optional season list."""
    sql = base_record_sql() + " WHERE m.id = ? GROUP BY m.id"
    row = conn.execute(sql, (media_id,)).fetchone()
    if row is None:
        return None
    record = row_to_record(row)
    if include_seasons and record.get("media_type") == "series":
        seasons_rows = conn.execute(
            "SELECT season_number, episode_count, watched_episodes FROM series_seasons WHERE media_id = ? ORDER BY season_number ASC",
            (media_id,),
        ).fetchall()
        record["seasons"] = [dict(s) for s in seasons_rows]
    return record


def add_media(
    conn: sqlite3.Connection,
    title: str,
    media_type: str,
    is_anime: bool = False,
    status: str = "planned",
    release_year: int | None = None,
    rating: int | None = None,
    note: str | None = None,
    tmdb_id: int | None = None,
    imdb_id: str | None = None,
    poster_path: str | None = None,
    overview: str | None = None,
    genres: str | None = None,
    original_title: str | None = None,
    director: str | None = None,
    cast_members: str | None = None,
    runtime: int | None = None,
    tmdb_rating: float | None = None,
    imdb_rating: float | None = None,
    tags: str | None = None,
    trailer_key: str | None = None,
) -> int:
    """Insert a new media record and return its generated ID."""
    if not tags:
        tag_list = []
        if genres:
            try:
                tag_list = json.loads(genres) if genres.startswith("[") else [g.strip() for g in genres.split(",") if g.strip()]
            except Exception:
                tag_list = [g.strip() for g in genres.split(",") if g.strip()]
        if is_anime and "Anime" not in tag_list:
            tag_list.append("Anime")
        if tag_list:
            tags = json.dumps(tag_list, ensure_ascii=False)

    cur = conn.execute(
        """
        INSERT INTO media (title, media_type, is_anime, status, release_year, rating, note,
                           tmdb_id, imdb_id, poster_path, overview, genres, original_title,
                           director, cast_members, runtime, tmdb_rating, imdb_rating, tags, trailer_key)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (title.strip(), media_type, int(is_anime), status, release_year, rating, note,
         tmdb_id, imdb_id, poster_path, overview, genres, original_title,
         director, cast_members, runtime, tmdb_rating, imdb_rating, tags, trailer_key),
    )
    conn.commit()
    return int(cur.lastrowid)


def update_media(conn: sqlite3.Connection, media_id: int, **fields: Any) -> bool:
    """Update specific fields of a media record. Returns True if row was found."""
    allowed = {
        "title", "media_type", "is_anime", "status", "release_year", "rating", "note",
        "tmdb_id", "imdb_id", "poster_path", "overview", "genres", "original_title",
        "director", "cast_members", "runtime", "tmdb_rating", "imdb_rating", "tags", "trailer_key",
        "watched_at", "times_watched", "is_favorite",
    }
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return False
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [media_id]
    result = conn.execute(f"UPDATE media SET {set_clause} WHERE id = ?", values)
    conn.commit()
    return result.rowcount > 0


def delete_media(conn: sqlite3.Connection, media_id: int) -> bool:
    """Delete a media record and its related details. Returns True if deleted."""
    result = conn.execute("DELETE FROM media WHERE id = ?", (media_id,))
    conn.commit()
    return result.rowcount > 0


def add_series_season(
    conn: sqlite3.Connection,
    media_id: int,
    season_number: int,
    episode_count: int | None = None,
    watched_episodes: int = 0,
) -> None:
    """Add or replace a season for a series."""
    conn.execute(
        """
        INSERT OR REPLACE INTO series_seasons (media_id, season_number, episode_count, watched_episodes)
        VALUES (?, ?, ?, ?)
        """,
        (media_id, season_number, episode_count, watched_episodes),
    )
    conn.commit()


def import_from_imdb(conn: sqlite3.Connection, imdb_data: dict[str, Any], is_anime: bool = False) -> int:
    """Import a media record from mapped IMDb data. Returns new media ID."""
    seasons = imdb_data.pop("seasons", [])
    imdb_data.pop("poster_url", None)

    media_id = add_media(
        conn,
        title=imdb_data.get("title", "Untitled"),
        media_type=imdb_data.get("media_type", "movie"),
        is_anime=is_anime,
        status="planned",
        release_year=imdb_data.get("release_year"),
        rating=None,
        note=None,
        imdb_id=imdb_data.get("imdb_id"),
        overview=imdb_data.get("overview"),
        genres=imdb_data.get("genres"),
        original_title=imdb_data.get("original_title"),
        director=imdb_data.get("director"),
        cast_members=imdb_data.get("cast"),
        runtime=imdb_data.get("runtime"),
        imdb_rating=imdb_data.get("imdb_rating"),
        tags=imdb_data.get("tags"),
        trailer_key=imdb_data.get("trailer_key"),
    )

    if imdb_data.get("media_type") == "series" and seasons:
        for season in seasons:
            sn = season.get("season_number", 0)
            if sn < 1:
                continue
            ep_count = season.get("episode_count")
            add_series_season(conn, media_id, sn, ep_count, 0)

    return media_id


def import_from_tmdb(conn: sqlite3.Connection, tmdb_data: dict[str, Any]) -> int:
    """Import a media record from mapped TMDB data. Returns new media ID."""
    seasons = tmdb_data.pop("seasons", [])
    media_id = add_media(conn, **tmdb_data)
    if tmdb_data.get("media_type") == "series" and seasons:
        for season in seasons:
            sn = season.get("season_number", 0)
            if sn < 1:
                continue
            ep_count = season.get("episode_count")
            add_series_season(conn, media_id, sn, ep_count, 0)
    return media_id


def get_advanced_stats(conn: sqlite3.Connection) -> dict[str, Any]:
    """Calculate watch time, top directors, top genres, and available tags."""
    movie_minutes = conn.execute(
        "SELECT SUM(COALESCE(runtime, 110)) FROM media WHERE media_type = 'movie' AND status = 'completed'"
    ).fetchone()[0] or 0

    series_episodes = conn.execute(
        "SELECT SUM(COALESCE(ss.watched_episodes, 0)) FROM series_seasons ss "
        "JOIN media m ON m.id = ss.media_id WHERE m.status IN ('completed', 'in_progress')"
    ).fetchone()[0] or 0
    series_minutes = series_episodes * 45

    total_minutes = movie_minutes + series_minutes
    total_hours = round(total_minutes / 60, 1)
    total_days = round(total_hours / 24, 1)

    director_counts: dict[str, int] = {}
    for row in conn.execute("SELECT director FROM media WHERE director IS NOT NULL AND director != ''"):
        for d in row[0].split(","):
            name = d.strip()
            if name:
                director_counts[name] = director_counts.get(name, 0) + 1
    top_directors = sorted(director_counts.items(), key=lambda x: x[1], reverse=True)[:8]

    cast_counts: dict[str, int] = {}
    for row in conn.execute("SELECT cast_members FROM media WHERE cast_members IS NOT NULL AND cast_members != ''"):
        for c in row[0].split(","):
            name = c.strip()
            if name:
                cast_counts[name] = cast_counts.get(name, 0) + 1
    top_cast = sorted(cast_counts.items(), key=lambda x: x[1], reverse=True)[:8]

    genre_counts: dict[str, int] = {}
    for row in conn.execute("SELECT genres FROM media WHERE genres IS NOT NULL AND genres != ''"):
        raw = row[0]
        try:
            glist = json.loads(raw) if raw.startswith("[") else [g.strip() for g in raw.split(",")]
        except Exception:
            glist = [g.strip() for g in raw.split(",")]
        for g in glist:
            if g:
                genre_counts[g] = genre_counts.get(g, 0) + 1
    top_genres = sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    decade_counts: dict[str, int] = {}
    for row in conn.execute("SELECT release_year FROM media WHERE release_year IS NOT NULL"):
        year = int(row[0])
        decade = f"{(year // 10) * 10}'ler"
        decade_counts[decade] = decade_counts.get(decade, 0) + 1
    sorted_decades = sorted(decade_counts.items(), key=lambda x: x[0], reverse=True)

    tags_set: set[str] = set()
    for row in conn.execute("SELECT tags FROM media WHERE tags IS NOT NULL AND tags != ''"):
        raw = row[0]
        try:
            tlist = json.loads(raw) if raw.startswith("[") else [t.strip() for t in raw.split(",")]
        except Exception:
            tlist = [t.strip() for t in raw.split(",")]
        for t in tlist:
            if t:
                tags_set.add(t)

    total_records = conn.execute("SELECT COUNT(*) FROM media").fetchone()[0] or 0
    completed_records = conn.execute("SELECT COUNT(*) FROM media WHERE status = 'completed'").fetchone()[0] or 0
    in_progress_records = conn.execute("SELECT COUNT(*) FROM media WHERE status = 'in_progress'").fetchone()[0] or 0
    planned_records = conn.execute("SELECT COUNT(*) FROM media WHERE status = 'planned'").fetchone()[0] or 0

    movie_count = conn.execute("SELECT COUNT(*) FROM media WHERE media_type = 'movie'").fetchone()[0] or 0
    series_count = conn.execute("SELECT COUNT(*) FROM media WHERE media_type = 'series'").fetchone()[0] or 0
    anime_count = conn.execute("SELECT COUNT(*) FROM media WHERE is_anime = 1").fetchone()[0] or 0

    completion_rate = round((completed_records / total_records * 100), 1) if total_records > 0 else 0.0

    last_30_days_rows = conn.execute(
        """
        SELECT id, title, release_year, rating, imdb_rating, tmdb_rating, poster_path, media_type, is_anime, runtime, updated_at, genres
        FROM media
        WHERE (status = 'completed' OR status = 'in_progress')
          AND (updated_at >= datetime('now', '-30 days') OR created_at >= datetime('now', '-30 days'))
        ORDER BY updated_at DESC
        """
    ).fetchall()

    last_30_items = [dict(r) for r in last_30_days_rows]
    last_30_movies = len(last_30_items)
    last_30_minutes = sum(r.get("runtime") or 110 for r in last_30_items)
    last_30_hours = round(last_30_minutes / 60, 1)

    runtime_stats = conn.execute(
        """
        SELECT AVG(runtime), MAX(runtime), MIN(runtime)
        FROM media
        WHERE media_type = 'movie' AND runtime IS NOT NULL AND runtime > 0
        """
    ).fetchone()
    avg_runtime = round(runtime_stats[0], 0) if runtime_stats and runtime_stats[0] else 115
    max_runtime = runtime_stats[1] if runtime_stats and runtime_stats[1] else None
    min_runtime = runtime_stats[2] if runtime_stats and runtime_stats[2] else None

    longest_movie = None
    if max_runtime:
        l_row = conn.execute("SELECT title, runtime FROM media WHERE runtime = ? LIMIT 1", (max_runtime,)).fetchone()
        if l_row:
            longest_movie = {"title": l_row[0], "runtime": l_row[1]}

    shortest_movie = None
    if min_runtime:
        s_row = conn.execute("SELECT title, runtime FROM media WHERE runtime = ? LIMIT 1", (min_runtime,)).fetchone()
        if s_row:
            shortest_movie = {"title": s_row[0], "runtime": s_row[1]}

    total_genre_occurrences = sum(genre_counts.values()) or 1
    genre_percentages = [
        {"name": g, "count": cnt, "percent": round((cnt / total_genre_occurrences) * 100, 1)}
        for g, cnt in top_genres
    ]

    tier_9_10 = conn.execute("SELECT COUNT(*) FROM media WHERE rating IN (9, 10)").fetchone()[0] or 0
    tier_7_8 = conn.execute("SELECT COUNT(*) FROM media WHERE rating IN (7, 8)").fetchone()[0] or 0
    tier_5_6 = conn.execute("SELECT COUNT(*) FROM media WHERE rating IN (5, 6)").fetchone()[0] or 0
    tier_1_4 = conn.execute("SELECT COUNT(*) FROM media WHERE rating IN (1, 2, 3, 4)").fetchone()[0] or 0
    rated_total = tier_9_10 + tier_7_8 + tier_5_6 + tier_1_4

    rating_tiers = {
        "masterpiece": {"count": tier_9_10, "percent": round((tier_9_10 / rated_total * 100), 1) if rated_total else 0},
        "great": {"count": tier_7_8, "percent": round((tier_7_8 / rated_total * 100), 1) if rated_total else 0},
        "average": {"count": tier_5_6, "percent": round((tier_5_6 / rated_total * 100), 1) if rated_total else 0},
        "low": {"count": tier_1_4, "percent": round((tier_1_4 / rated_total * 100), 1) if rated_total else 0},
        "rated_total": rated_total,
    }

    top_rated_rows = conn.execute(
        """
        SELECT id, title, release_year, rating, imdb_rating, tmdb_rating, poster_path, media_type, is_anime
        FROM media
        WHERE (rating >= 8 OR imdb_rating >= 8.5)
        ORDER BY COALESCE(rating, imdb_rating) DESC
        LIMIT 6
        """
    ).fetchall()
    top_rated = [dict(r) for r in top_rated_rows]

    diary_rows = conn.execute(
        """
        SELECT id, title, release_year, rating, imdb_rating, poster_path, watched_at, times_watched, media_type, is_anime, director
        FROM media
        WHERE status = 'completed'
        ORDER BY COALESCE(watched_at, created_at) DESC
        LIMIT 10
        """
    ).fetchall()
    diary = [dict(r) for r in diary_rows]

    month_names = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]
    monthly_activity = []
    for m_idx in range(1, 13):
        m_str = f"{m_idx:02d}"
        cnt = conn.execute(
            """
            SELECT COUNT(*), SUM(COALESCE(runtime, 0))
            FROM media
            WHERE status = 'completed' AND (strftime('%m', watched_at) = ? OR (watched_at IS NULL AND strftime('%m', created_at) = ?))
            """,
            (m_str, m_str)
        ).fetchone()
        count = cnt[0] or 0
        minutes = cnt[1] or 0
        monthly_activity.append({
            "month_num": m_idx,
            "month_name": month_names[m_idx - 1],
            "count": count,
            "hours": round(minutes / 60, 1),
        })

    return {
        "watch_time": {
            "total_minutes": total_minutes,
            "total_hours": total_hours,
            "total_days": total_days,
            "movie_hours": round(movie_minutes / 60, 1),
            "series_hours": round(series_minutes / 60, 1),
        },
        "last_30_days": {
            "count": last_30_movies,
            "hours": last_30_hours,
            "minutes": last_30_minutes,
            "items": last_30_items,
        },
        "rates": {
            "completion_rate": completion_rate,
            "movie_percent": round((movie_count / total_records * 100), 1) if total_records else 0,
            "series_percent": round((series_count / total_records * 100), 1) if total_records else 0,
            "anime_percent": round((anime_count / total_records * 100), 1) if total_records else 0,
            "movie_count": movie_count,
            "series_count": series_count,
            "anime_count": anime_count,
            "total_records": total_records,
            "completed_records": completed_records,
            "in_progress_records": in_progress_records,
            "planned_records": planned_records,
        },
        "runtime_analysis": {
            "avg_movie_runtime": avg_runtime,
            "longest_movie": longest_movie,
            "shortest_movie": shortest_movie,
        },
        "rating_tiers": rating_tiers,
        "top_directors": [{"name": d[0], "count": d[1]} for d in top_directors],
        "top_cast": [{"name": c[0], "count": c[1]} for c in top_cast],
        "top_genres": genre_percentages,
        "decades": [{"decade": dec[0], "count": dec[1]} for dec in sorted_decades],
        "top_rated": top_rated,
        "diary": diary,
        "monthly_activity": monthly_activity,
        "tags": sorted(tags_set),
    }


def export_records_json(conn: sqlite3.Connection) -> str:
    """Export all media records and seasons as formatted JSON."""
    rows = conn.execute(base_record_sql() + " GROUP BY m.id ORDER BY m.id ASC").fetchall()
    records = []
    for r in rows:
        rec = row_to_record(r)
        if rec["media_type"] == "series":
            s_rows = conn.execute(
                "SELECT season_number, episode_count, watched_episodes FROM series_seasons WHERE media_id = ? ORDER BY season_number",
                (rec["id"],),
            ).fetchall()
            rec["seasons"] = [dict(s) for s in s_rows]
        records.append(rec)
    return json.dumps(records, ensure_ascii=False, indent=2, default=str)


def export_records_csv(conn: sqlite3.Connection) -> str:
    """Export media records as standard CSV."""
    rows = conn.execute(base_record_sql() + " GROUP BY m.id ORDER BY m.id ASC").fetchall()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id", "title", "original_title", "media_type", "is_anime", "status",
        "release_year", "rating", "imdb_rating", "tmdb_rating", "director",
        "genres", "tags", "note", "created_at"
    ])
    for r in rows:
        rec = row_to_record(r)
        genres_str = ", ".join(rec.get("genres", []))
        tags_str = ", ".join(rec.get("tags", []))
        writer.writerow([
            rec["id"], rec["title"], rec.get("original_title", ""), rec["media_type"],
            int(rec["is_anime"]), rec["status"], rec.get("release_year") or "",
            rec.get("rating") or "", rec.get("imdb_rating") or "", rec.get("tmdb_rating") or "",
            rec.get("director", ""), genres_str, tags_str, rec.get("note", ""), rec.get("created_at", "")
        ])
    return output.getvalue()


def export_records_letterboxd_csv(conn: sqlite3.Connection) -> str:
    """Export media records matching Letterboxd's official diary import format."""
    rows = conn.execute(base_record_sql() + " WHERE m.media_type = 'movie' GROUP BY m.id ORDER BY m.id ASC").fetchall()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Title", "Year", "Rating10", "WatchedDate", "Review"])
    for r in rows:
        rec = row_to_record(r)
        writer.writerow([
            rec["title"],
            rec.get("release_year") or "",
            rec.get("rating") or "",
            rec.get("watched_at") or (rec.get("created_at", "")[:10] if rec.get("status") == "completed" else ""),
            rec.get("note") or ""
        ])
    return output.getvalue()


def reset_database(db_path: Path) -> None:
    """Completely wipe and recreate the database with an empty schema."""
    if db_path.is_file():
        db_path.unlink()
    ensure_schema(db_path)


# =====================================================================
# 2. TMDB CLIENT MODULE
# =====================================================================

def load_tmdb_api_key() -> str | None:
    """Load TMDB API key from environment or .env file."""
    key = os.environ.get("TMDB_API_KEY")
    if key:
        return key.strip()
    env_path = ROOT / ".env"
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


def get_tmdb_api_key() -> str:
    """Return the TMDB API key or raise an error."""
    key = load_tmdb_api_key()
    if not key:
        raise RuntimeError("TMDB_API_KEY bulunamadı. .env dosyasına veya çevre değişkenlerine ekleyin.")
    return key


def tmdb_request(path: str, params: dict[str, str] | None = None) -> dict[str, Any]:
    """Make a GET request to the TMDB API and return parsed JSON."""
    api_key = get_tmdb_api_key()
    headers = {
        "Accept": "application/json",
        "User-Agent": "MediaTracker/1.0",
    }
    query_params = {}
    if params:
        query_params.update(params)

    if len(api_key) > 50 or api_key.startswith("eyJ"):
        headers["Authorization"] = f"Bearer {api_key}"
    else:
        query_params["api_key"] = api_key

    query_str = f"?{urllib.parse.urlencode(query_params)}" if query_params else ""
    url = f"{TMDB_BASE_URL}{path}{query_str}"

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        time.sleep(TMDB_REQUEST_DELAY)
        return data
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        LOGGER.error("TMDB API error %d for %s: %s", e.code, path, body[:200])
        raise
    except urllib.error.URLError as e:
        LOGGER.error("TMDB connection error for %s: %s", path, e.reason)
        raise


def tmdb_search_movie(query: str, year: int | None = None, language: str = TMDB_DEFAULT_LANG, page: int = 1) -> dict[str, Any]:
    params = {"query": query, "language": language, "page": str(page)}
    if year:
        params["year"] = str(year)
    return tmdb_request("/search/movie", params)


def tmdb_search_tv(query: str, year: int | None = None, language: str = TMDB_DEFAULT_LANG, page: int = 1) -> dict[str, Any]:
    params = {"query": query, "language": language, "page": str(page)}
    if year:
        params["first_air_date_year"] = str(year)
    return tmdb_request("/search/tv", params)


def tmdb_search_multi(query: str, language: str = TMDB_DEFAULT_LANG, page: int = 1) -> dict[str, Any]:
    return tmdb_request("/search/multi", {"query": query, "language": language, "page": str(page)})


def tmdb_get_movie(tmdb_id: int, language: str = TMDB_DEFAULT_LANG) -> dict[str, Any]:
    return tmdb_request(f"/movie/{tmdb_id}", {"language": language})


def tmdb_get_tv(tmdb_id: int, language: str = TMDB_DEFAULT_LANG) -> dict[str, Any]:
    return tmdb_request(f"/tv/{tmdb_id}", {"language": language})


def tmdb_find_by_imdb(imdb_id: str, language: str = TMDB_DEFAULT_LANG) -> dict[str, Any] | None:
    try:
        data = tmdb_request(f"/find/{imdb_id}", {"external_source": "imdb_id", "language": language})
        movies = data.get("movie_results", [])
        if movies:
            return movies[0]
        tvs = data.get("tv_results", [])
        if tvs:
            return tvs[0]
    except Exception as e:
        LOGGER.warning("TMDB find_by_imdb failed for %s: %s", imdb_id, e)
    return None


def tmdb_get_random_trending(media_type: str = "all", language: str = TMDB_DEFAULT_LANG) -> dict[str, Any] | None:
    path = f"/trending/{'movie' if media_type == 'movie' else ('tv' if media_type == 'series' else 'all')}/week"
    try:
        data = tmdb_request(path, {"language": language})
        results = data.get("results", [])
        valid = [r for r in results if r.get("poster_path") and (r.get("title") or r.get("name"))]
        if valid:
            item = random.choice(valid)
            return tmdb_search_result_to_summary(item)
    except Exception as e:
        LOGGER.warning("TMDB random trending failed: %s", e)
    return None


def tmdb_poster_url(poster_path: str, size: str = TMDB_DEFAULT_POSTER_SIZE) -> str:
    return f"{TMDB_IMAGE_BASE}/{size}{poster_path}"


def tmdb_download_poster(poster_path: str, dest: Path, size: str = TMDB_DEFAULT_POSTER_SIZE, overwrite: bool = False) -> bool:
    if not poster_path:
        return False
    if dest.is_file() and not overwrite:
        return False
    url = tmdb_poster_url(poster_path, size)
    req = urllib.request.Request(url, headers={"User-Agent": "MediaTracker/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(resp.read())
        time.sleep(TMDB_REQUEST_DELAY)
        LOGGER.info("Downloaded poster: %s -> %s", poster_path, dest.name)
        return True
    except Exception as e:
        LOGGER.warning("Poster download failed for %s: %s", poster_path, e)
        return False


def tmdb_movie_to_media(tmdb_data: dict[str, Any]) -> dict[str, Any]:
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
        "is_anime": False,
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


def tmdb_tv_to_media(tmdb_data: dict[str, Any]) -> dict[str, Any]:
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
        "is_anime": False,
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


def tmdb_search_result_to_summary(item: dict[str, Any]) -> dict[str, Any]:
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
        "poster_preview": tmdb_poster_url(item["poster_path"], "w185") if item.get("poster_path") else None,
    }


# =====================================================================
# 3. IMDB & CINEMETA CLIENT MODULE
# =====================================================================

def imdb_slugify_search(query: str) -> str:
    q = query.lower().strip()
    q = re.sub(r"[^a-z0-9_ -]", "", q)
    q = re.sub(r"[\s-]+", "_", q)
    return q if q else "a"


def imdb_search(query: str) -> list[dict[str, Any]]:
    clean_q = imdb_slugify_search(query)
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
            continue
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


def imdb_get_details(imdb_id: str, media_type: str = "movie") -> dict[str, Any]:
    cinemeta_type = "series" if media_type == "series" else "movie"
    url = f"{CINEMETA_URL}/{cinemeta_type}/{imdb_id}.json"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
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

    year = None
    year_raw = meta.get("year") or meta.get("releaseInfo")
    if year_raw:
        m = re.search(r"\b(19\d\d|20\d\d)\b", str(year_raw))
        if m:
            year = int(m.group(1))

    rating = None
    rating_raw = meta.get("imdbRating")
    if rating_raw:
        try:
            rating = float(rating_raw)
        except (ValueError, TypeError):
            pass

    runtime = None
    rt_raw = meta.get("runtime")
    if rt_raw:
        m = re.search(r"(\d+)", str(rt_raw))
        if m:
            runtime = int(m.group(1))

    genres = meta.get("genre") or meta.get("genres") or []
    if isinstance(genres, str):
        genres = [g.strip() for g in genres.split(",")]

    director = meta.get("director") or []
    if isinstance(director, list):
        director = ", ".join(director)
    cast = meta.get("cast") or []
    if isinstance(cast, list):
        cast = ", ".join(cast[:5])

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


def imdb_get_random_top() -> dict[str, Any] | None:
    top_queries = [
        "godfather", "shawshank", "dark_knight", "pulp_fiction", "inception",
        "matrix", "interstellar", "fight_club", "spirited_away", "se7en",
        "forrest_gump", "goodfellas", "gladiator", "oppenheimer", "blade_runner",
        "alien", "psycho", "casablanca", "whiplash", "parasite", "spider_man"
    ]
    query = random.choice(top_queries)
    results = imdb_search(query)
    if results:
        best = results[0]
        details = imdb_get_details(best["imdb_id"], best["media_type"])
        return details if details else best
    return None


def imdb_download_poster(image_url: str, dest: Path, overwrite: bool = False) -> bool:
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


# =====================================================================
# 4. POSTER FETCHER
# =====================================================================

def batch_match_and_update(conn: sqlite3.Connection, record: dict[str, Any], dry_run: bool = False) -> str | None:
    title = record["title"]
    year = record.get("release_year")
    media_type = record["media_type"]
    media_id = record["id"]

    try:
        if media_type == "movie":
            results = tmdb_search_movie(title, year=year)
        else:
            results = tmdb_search_tv(title, year=year)
    except Exception as e:
        print(f"  [!] Arama hatası: {e}")
        return None

    items = results.get("results", [])
    if not items:
        print(f"  [-] TMDB'de bulunamadı: {title}")
        return None

    best = items[0]
    tmdb_id = best.get("id")
    poster_path = best.get("poster_path")
    tmdb_title = best.get("title") or best.get("name") or "?"
    print(f"  -> Eşleşme: {tmdb_title} (TMDB #{tmdb_id})")

    if not dry_run and tmdb_id:
        try:
            conn.execute("UPDATE media SET tmdb_id = ?, poster_path = ? WHERE id = ?", (tmdb_id, poster_path, media_id))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.execute("UPDATE media SET poster_path = ? WHERE id = ?", (poster_path, media_id))
            conn.commit()

    return poster_path


def run_batch_fetch_posters(db_path: Path, force: bool = False, dry_run: bool = False, match_missing: bool = False) -> None:
    ensure_schema(db_path)
    POSTERS_DIR.mkdir(parents=True, exist_ok=True)
    conn = connect(db_path)
    try:
        rows = conn.execute(
            "SELECT id, title, media_type, release_year, tmdb_id, poster_path "
            "FROM media WHERE media_type != 'book' ORDER BY id"
        ).fetchall()
        total = len(rows)
        downloaded = 0
        matched = 0
        skipped = 0

        print(f"Toplam {total} kayıt bulundu.\n")
        for i, row in enumerate(rows, 1):
            record = dict(row)
            title = record["title"]
            media_id = record["id"]
            progress = f"[{i}/{total}]"

            if not record.get("tmdb_id") and match_missing:
                print(f"{progress} Aranıyor: {title}")
                poster_path = batch_match_and_update(conn, record, dry_run=dry_run)
                if poster_path:
                    record["poster_path"] = poster_path
                    matched += 1
            elif not record.get("tmdb_id"):
                print(f"{progress} Atlanıyor (tmdb_id yok): {title}")
                skipped += 1
                continue

            if not record.get("poster_path"):
                print(f"{progress} Poster yolu yok: {title}")
                skipped += 1
                continue

            dest = POSTERS_DIR / f"{media_id}.jpg"
            if dest.is_file() and not force:
                print(f"{progress} Mevcut: {title}")
                continue

            if dry_run:
                print(f"{progress} İndirilecek: {title} → {dest.name}")
                downloaded += 1
                continue

            print(f"{progress} İndiriliyor: {title}...", end=" ", flush=True)
            if tmdb_download_poster(record["poster_path"], dest, overwrite=force):
                print("[OK]")
                downloaded += 1
            else:
                print("[FAIL]")

        print(f"\n{'-' * 40}")
        print(f"Toplam: {total} | İndirilen: {downloaded} | Eşleşen: {matched} | Atlanan: {skipped}")
        if dry_run:
            print("(Dry-run modu — hiçbir dosya indirilmedi.)")
    finally:
        conn.close()


# =====================================================================
# 5. HTTP SERVER & REST API
# =====================================================================

@dataclass(frozen=True)
class QueryOptions:
    kind: str = "all"
    status: str | None = None
    tag: str | None = None
    query: str = ""
    sort: str = "updated_at"
    direction: str = "desc"
    limit: int = DEFAULT_LIMIT
    offset: int = 0
    min_rating: float | None = None
    min_year: int | None = None
    max_year: int | None = None
    max_runtime: int | None = None
    is_favorite: bool | None = None

    @classmethod
    def from_params(cls: type[QueryOptions], params: dict[str, list[str]]) -> QueryOptions:
        kind = first_param(params, "kind", "all")
        if kind not in GALLERY_FILTERS:
            kind = "all"
        status_raw = first_param(params, "status", "")
        status = status_raw if status_raw in STATUSES else None
        tag = first_param(params, "tag", "").strip() or None
        query = first_param(params, "q", "").strip()
        sort = first_param(params, "sort", "updated_at")
        if sort not in SORT_COLUMNS:
            sort = "updated_at"
        direction = first_param(params, "dir", "desc").lower()
        if direction not in {"asc", "desc"}:
            direction = "desc"
        limit = max(1, min(parse_int_param(params, "limit", DEFAULT_LIMIT), MAX_LIMIT))
        offset = max(0, parse_int_param(params, "offset", 0))

        min_rating_raw = first_param(params, "min_rating", "")
        min_rating = float(min_rating_raw) if min_rating_raw else None

        min_year_raw = first_param(params, "min_year", "")
        min_year = int(min_year_raw) if min_year_raw else None

        max_year_raw = first_param(params, "max_year", "")
        max_year = int(max_year_raw) if max_year_raw else None

        max_runtime_raw = first_param(params, "max_runtime", "")
        max_runtime = int(max_runtime_raw) if max_runtime_raw else None

        fav_raw = first_param(params, "favorite", "").lower()
        is_favorite = True if fav_raw in ("1", "true", "yes") else None

        return cls(kind, status, tag, query, sort, direction, limit, offset, min_rating, min_year, max_year, max_runtime, is_favorite)


def first_param(params: dict[str, list[str]], name: str, default: str) -> str:
    values = params.get(name)
    return values[0] if values else default


def parse_int_param(params: dict[str, list[str]], name: str, default: int) -> int:
    try:
        return int(first_param(params, name, str(default)))
    except ValueError:
        return default


def slugify(title: str) -> str:
    s = re.sub(r'[\\/:*?"<>|]', "", title)
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) > 120:
        s = s[:120].rstrip()
    return s if s else "untitled"


def poster_url_for(record: dict[str, Any]) -> str | None:
    media_id = record.get("id")
    title = record.get("title") or ""
    if media_id is not None:
        by_id = POSTERS_DIR / f"{media_id}.jpg"
        if by_id.is_file():
            return f"/static/posters/{media_id}.jpg"
    slug = slugify(str(title))
    by_slug = POSTERS_DIR / f"{slug}.jpg"
    if by_slug.is_file():
        return f"/static/posters/{slug}.jpg"
    return None


def enrich_with_poster(record: dict[str, Any]) -> dict[str, Any]:
    url = poster_url_for(record)
    enriched = dict(record)
    enriched["poster_url"] = url
    enriched["has_poster"] = url is not None
    return enriched


def gallery_where_adjust(where: str) -> str:
    if "WHERE" in where:
        return where + f" AND {GALLERY_KINDS_SQL_EXCLUDE_BOOK}"
    return f"WHERE {GALLERY_KINDS_SQL_EXCLUDE_BOOK}"


def records_payload(db_path: Path, params: dict[str, list[str]]) -> dict[str, Any]:
    options = QueryOptions.from_params(params)
    where, values = media_where(
        options.kind,
        options.query,
        options.status,
        options.tag,
        options.min_rating,
        options.min_year,
        options.max_year,
        options.max_runtime,
        options.is_favorite,
    )
    where = gallery_where_adjust(where)
    count_sql = (
        "SELECT COUNT(DISTINCT m.id) FROM media AS m "
        "LEFT JOIN book_details AS bd ON bd.media_id = m.id "
        f"{where}"
    )
    order_expr = SORT_COLUMNS[options.sort]
    direction = options.direction.upper()
    data_sql = (
        base_record_sql()
        + f" {where} GROUP BY m.id "
        + f"ORDER BY {order_expr} IS NULL ASC, {order_expr} {direction}, m.id ASC "
        + "LIMIT ? OFFSET ?"
    )
    conn = connect(db_path)
    try:
        total = int(conn.execute(count_sql, values).fetchone()[0])
        rows = conn.execute(data_sql, [*values, options.limit, options.offset]).fetchall()
        records = [enrich_with_poster(row_to_record(row)) for row in rows]
        return {
            "records": records,
            "total": total,
            "limit": options.limit,
            "offset": options.offset,
            "kind": options.kind,
            "status": options.status,
            "tag": options.tag,
            "query": options.query,
            "sort": options.sort,
            "dir": options.direction,
        }
    finally:
        conn.close()


def record_payload(db_path: Path, media_id: int) -> dict[str, Any] | None:
    conn = connect(db_path)
    try:
        record = fetch_media(conn, media_id, include_seasons=True)
        if record is None or record.get("media_type") == "book":
            return None
        return enrich_with_poster(record)
    finally:
        conn.close()


def summary_payload(db_path: Path) -> dict[str, Any]:
    conn = connect(db_path)
    try:
        def scalar(sql: str, values: tuple[Any, ...] = (), fallback: Any = 0) -> Any:
            v = conn.execute(sql, values).fetchone()[0]
            return fallback if v is None else v

        counts = {
            "movie": int(scalar("SELECT COUNT(*) FROM media WHERE media_type = 'movie' AND is_anime = 0")),
            "anime-movie": int(scalar("SELECT COUNT(*) FROM media WHERE media_type = 'movie' AND is_anime = 1")),
            "series": int(scalar("SELECT COUNT(*) FROM media WHERE media_type = 'series' AND is_anime = 0")),
            "anime-series": int(scalar("SELECT COUNT(*) FROM media WHERE media_type = 'series' AND is_anime = 1")),
        }
        counts["anime"] = counts["anime-movie"] + counts["anime-series"]
        counts["all"] = sum(counts[key] for key in ("movie", "anime-movie", "series", "anime-series"))
        counts["book"] = 0
        status_counts = {
            status: int(scalar("SELECT COUNT(*) FROM media WHERE status = ? AND media_type != 'book'", (status,)))
            for status in STATUSES
        }
        rating_row = conn.execute("SELECT COUNT(rating), AVG(rating) FROM media WHERE rating IS NOT NULL AND media_type != 'book'").fetchone()
        rating_count = int(rating_row[0] or 0)
        buckets = [0] * 11
        for rating, count in conn.execute(
            "SELECT rating, COUNT(*) FROM media WHERE rating IS NOT NULL AND media_type != 'book' GROUP BY rating"
        ):
            buckets[int(rating)] = int(count)

        try:
            poster_files = list(POSTERS_DIR.glob("*.jpg"))
            id_posters = len([p for p in poster_files if p.stem.isdigit()])
            poster_size_mb = round(sum(p.stat().st_size for p in poster_files) / (1024 * 1024), 2)
        except Exception:
            id_posters = 0
            poster_files = []
            poster_size_mb = 0.0

        try:
            db_size_kb = round(db_path.stat().st_size / 1024, 1)
        except Exception:
            db_size_kb = 0.0

        try:
            integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        except Exception:
            integrity = "ok"

        advanced = get_advanced_stats(conn)

        return {
            "db_path": str(db_path),
            "db_size_kb": db_size_kb,
            "schema_version": SCHEMA_VERSION,
            "sqlite_integrity": integrity,
            "counts": counts,
            "status_counts": status_counts,
            "avg_rating": rating_row[1],
            "rating_count": rating_count,
            "rating_buckets": buckets,
            "posters": {
                "id_based": id_posters,
                "total_files": len(poster_files) if isinstance(poster_files, list) else 0,
                "size_mb": poster_size_mb,
            },
            "stats": advanced,
        }
    finally:
        conn.close()


def json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, ensure_ascii=False, indent=2, default=str).encode("utf-8")


def read_json_body(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    length = int(handler.headers.get("Content-Length", 0))
    if length == 0:
        return {}
    raw = handler.rfile.read(length)
    return json.loads(raw.decode("utf-8"))


def static_file_path(request_path: str) -> Path | None:
    if not request_path.startswith(STATIC_URL_PREFIX):
        return None
    relative_path = request_path.removeprefix(STATIC_URL_PREFIX)
    if not relative_path:
        return None
    candidate = (STATIC_DIR / relative_path).resolve()
    try:
        candidate.relative_to(STATIC_DIR.resolve())
    except ValueError:
        return None
    return candidate if candidate.is_file() else None


def file_content_type(path: Path) -> str:
    content_type, _ = mimetypes.guess_type(path.name)
    content_type = content_type or "application/octet-stream"
    if content_type.startswith("text/") or content_type in {"application/javascript", "application/json"}:
        return f"{content_type}; charset=utf-8"
    return content_type


def get_trailer_url(record: dict[str, Any]) -> str:
    if record.get("trailer_key"):
        return f"https://www.youtube-nocookie.com/embed/{record['trailer_key']}?autoplay=1"
    if record.get("tmdb_id"):
        try:
            mtype = "tv" if record.get("media_type") == "series" else "movie"
            vdata = tmdb_request(f"/{mtype}/{record['tmdb_id']}/videos", {"language": "tr-TR"})
            results = vdata.get("results", [])
            if not results:
                vdata = tmdb_request(f"/{mtype}/{record['tmdb_id']}/videos", {"language": "en-US"})
                results = vdata.get("results", [])
            for v in results:
                if v.get("site") == "YouTube" and v.get("key"):
                    return f"https://www.youtube-nocookie.com/embed/{v['key']}?autoplay=1"
        except Exception:
            pass
    q = f"{record.get('title', '')} {record.get('release_year', '')} fragman trailer"
    return f"https://www.youtube-nocookie.com/embed?listType=search&list={urllib.parse.quote(q)}&autoplay=1"


def make_handler(db_path: Path) -> type[BaseHTTPRequestHandler]:
    class GalleryHandler(BaseHTTPRequestHandler):
        server_version = SERVER_VERSION

        def send_bytes(self, status: HTTPStatus, body: bytes, content_type: str, extra_headers: dict[str, str] | None = None) -> None:
            self.send_response(status.value)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            if extra_headers and "Cache-Control" in extra_headers:
                self.send_header("Cache-Control", extra_headers["Cache-Control"])
            else:
                self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Access-Control-Allow-Origin", "*")
            if extra_headers:
                for k, v in extra_headers.items():
                    if k != "Cache-Control":
                        self.send_header(k, v)
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def send_json(self, status: HTTPStatus, payload: Any) -> None:
            self.send_bytes(status, json_bytes(payload), "application/json; charset=utf-8")

        def send_file(self, status: HTTPStatus, path: Path, max_age: int | None = None) -> None:
            extra_headers = {}
            if max_age is not None:
                extra_headers["Cache-Control"] = f"public, max-age={max_age}, immutable" if max_age > 86400 else f"public, max-age={max_age}"
            self.send_bytes(status, path.read_bytes(), file_content_type(path), extra_headers=extra_headers if extra_headers else None)

        def do_OPTIONS(self) -> None:  # noqa: N802
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, HEAD, POST, PUT, DELETE, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()

        def do_HEAD(self) -> None:  # noqa: N802
            self.do_GET()

        def do_GET(self) -> None:  # noqa: N802
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)

            if parsed.path in ("/", "/gallery", "/gallery/", "/stats", "/analytics"):
                if not TEMPLATE_PATH.is_file():
                    LOGGER.error("Gallery template is missing: %s", TEMPLATE_PATH)
                    self.send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": INTERNAL_ERROR_MESSAGE})
                    return
                self.send_file(HTTPStatus.OK, TEMPLATE_PATH)
                return

            if parsed.path == "/main-logo.svg":
                logo = STATIC_DIR / "main-logo.svg"
                if not logo.is_file():
                    self.send_json(HTTPStatus.NOT_FOUND, {"error": "Dosya bulunamadı."})
                    return
                self.send_file(HTTPStatus.OK, logo, max_age=604800)
                return

            if parsed.path.startswith(STATIC_URL_PREFIX):
                asset = static_file_path(parsed.path)
                if asset is None:
                    self.send_json(HTTPStatus.NOT_FOUND, {"error": "Dosya bulunamadı."})
                    return
                is_poster = parsed.path.startswith(POSTERS_URL_PREFIX)
                self.send_file(HTTPStatus.OK, asset, max_age=604800 if is_poster else 86400)
                return

            if parsed.path == "/api/records":
                try:
                    self.send_json(HTTPStatus.OK, records_payload(db_path, params))
                except Exception:
                    LOGGER.exception("Records API request failed")
                    self.send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": INTERNAL_ERROR_MESSAGE})
                return

            # Discover Random (Local Archive / TMDB / IMDb)
            if parsed.path in ("/api/random", "/api/discover/random"):
                source = first_param(params, "source", "archive").lower()
                media_type = first_param(params, "media_type", "movie")

                if source == "tmdb":
                    try:
                        rec = tmdb_get_random_trending(media_type=media_type, language="tr-TR")
                        if rec:
                            self.send_json(HTTPStatus.OK, {"source": "tmdb", "item": rec})
                            return
                    except Exception as e:
                        LOGGER.warning("TMDB discover random failed: %s", e)

                if source == "imdb":
                    try:
                        rec = imdb_get_random_top()
                        if rec:
                            self.send_json(HTTPStatus.OK, {"source": "imdb", "item": rec})
                            return
                    except Exception as e:
                        LOGGER.warning("IMDb discover random failed: %s", e)

                conn = connect(db_path)
                try:
                    options = QueryOptions.from_params(params)
                    where, values = media_where(options.kind, options.query, options.status, options.tag)
                    where = gallery_where_adjust(where)
                    sql = base_record_sql() + f" {where} GROUP BY m.id ORDER BY RANDOM() LIMIT 1"
                    row = conn.execute(sql, values).fetchone()
                    if not row:
                        self.send_json(HTTPStatus.NOT_FOUND, {"error": "Arşivde seçilecek uygun kayıt bulunamadı."})
                    else:
                        self.send_json(HTTPStatus.OK, {"source": "archive", "item": enrich_with_poster(row_to_record(row))})
                finally:
                    conn.close()
                return

            # Person Filmography
            if parsed.path == "/api/person/movies":
                name = first_param(params, "name", "").strip()
                if not name:
                    self.send_json(HTTPStatus.BAD_REQUEST, {"error": "İsim parametresi gereklidir."})
                    return
                try:
                    sdata = tmdb_request("/search/person", {"query": name, "language": "tr-TR"})
                    persons = sdata.get("results", [])
                    if not persons:
                        self.send_json(HTTPStatus.OK, {"person": {"name": name}, "movies": []})
                        return

                    p = persons[0]
                    pid = p.get("id")
                    profile_path = p.get("profile_path")
                    cdata = tmdb_request(f"/person/{pid}/movie_credits", {"language": "tr-TR"})
                    crew_and_cast = cdata.get("cast", []) + [c for c in cdata.get("crew", []) if c.get("job") == "Director"]
                    crew_and_cast.sort(key=lambda m: m.get("vote_count", 0), reverse=True)

                    seen_ids = set()
                    unique_movies = []
                    for m in crew_and_cast:
                        mid = m.get("id")
                        if mid and mid not in seen_ids and m.get("poster_path") and (m.get("title") or m.get("name")):
                            seen_ids.add(mid)
                            unique_movies.append(tmdb_search_result_to_summary(m))
                            if len(unique_movies) >= 6:
                                break

                    self.send_json(HTTPStatus.OK, {
                        "person": {
                            "id": pid,
                            "name": p.get("name"),
                            "known_for_department": p.get("known_for_department"),
                            "profile_url": f"https://image.tmdb.org/t/p/w200{profile_path}" if profile_path else None
                        },
                        "movies": unique_movies
                    })
                except Exception as e:
                    LOGGER.warning("Person lookup failed: %s", e)
                    self.send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(e)})
                return

            # Backup Export
            if parsed.path == "/api/export":
                fmt = first_param(params, "format", "json").lower()
                conn = connect(db_path)
                try:
                    if fmt == "letterboxd":
                        csv_data = export_records_letterboxd_csv(conn).encode("utf-8-sig")
                        self.send_bytes(
                            HTTPStatus.OK, csv_data, "text/csv; charset=utf-8",
                            {"Content-Disposition": 'attachment; filename="letterboxd-import.csv"'}
                        )
                    elif fmt == "csv":
                        csv_data = export_records_csv(conn).encode("utf-8-sig")
                        self.send_bytes(
                            HTTPStatus.OK, csv_data, "text/csv; charset=utf-8",
                            {"Content-Disposition": 'attachment; filename="media-tracker-export.csv"'}
                        )
                    else:
                        json_data = export_records_json(conn).encode("utf-8")
                        self.send_bytes(
                            HTTPStatus.OK, json_data, "application/json; charset=utf-8",
                            {"Content-Disposition": 'attachment; filename="media-tracker-backup.json"'}
                        )
                finally:
                    conn.close()
                return

            # Trailer
            if parsed.path.startswith("/api/records/") and parsed.path.endswith("/trailer"):
                try:
                    mid_str = parsed.path.removeprefix("/api/records/").removesuffix("/trailer")
                    media_id = int(mid_str)
                    rec = record_payload(db_path, media_id)
                    if not rec:
                        self.send_json(HTTPStatus.NOT_FOUND, {"error": "Kayıt bulunamadı."})
                        return
                    trailer_url = get_trailer_url(rec)
                    self.send_json(HTTPStatus.OK, {"title": rec["title"], "trailer_url": trailer_url})
                except Exception as e:
                    self.send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(e)})
                return

            # Similar Movies
            if parsed.path.startswith("/api/records/") and parsed.path.endswith("/similar"):
                try:
                    mid_str = parsed.path.removeprefix("/api/records/").removesuffix("/similar")
                    media_id = int(mid_str)
                    rec = record_payload(db_path, media_id)
                    if not rec:
                        self.send_json(HTTPStatus.NOT_FOUND, {"error": "Kayıt bulunamadı."})
                        return
                    similar_list = []
                    if rec.get("tmdb_id"):
                        try:
                            mtype = "tv" if rec.get("media_type") == "series" else "movie"
                            data = tmdb_request(f"/{mtype}/{rec['tmdb_id']}/recommendations", {"language": "tr-TR"})
                            results = data.get("results", [])[:4]
                            for r in results:
                                if r.get("poster_path") and (r.get("title") or r.get("name")):
                                    similar_list.append(tmdb_search_result_to_summary(r))
                        except Exception as err:
                            LOGGER.warning("TMDB recommendations failed: %s", err)
                    self.send_json(HTTPStatus.OK, {"results": similar_list})
                except Exception as e:
                    self.send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(e)})
                return

            if parsed.path.startswith("/api/records/"):
                try:
                    media_id = int(parsed.path.removeprefix("/api/records/"))
                    record = record_payload(db_path, media_id)
                    if record is None:
                        self.send_json(HTTPStatus.NOT_FOUND, {"error": "Kayıt bulunamadı."})
                    else:
                        self.send_json(HTTPStatus.OK, record)
                except ValueError:
                    self.send_json(HTTPStatus.BAD_REQUEST, {"error": "Geçersiz kayıt kimliği."})
                except Exception:
                    LOGGER.exception("Record detail API request failed")
                    self.send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": INTERNAL_ERROR_MESSAGE})
                return

            if parsed.path == "/api/summary":
                try:
                    self.send_json(HTTPStatus.OK, summary_payload(db_path))
                except Exception:
                    LOGGER.exception("Summary API request failed")
                    self.send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": INTERNAL_ERROR_MESSAGE})
                return

            if parsed.path == "/health":
                conn_h: sqlite3.Connection | None = None
                try:
                    conn_h = connect(db_path)
                    integrity = conn_h.execute("PRAGMA quick_check").fetchone()[0]
                    self.send_json(HTTPStatus.OK, {
                        "ok": integrity == "ok",
                        "db_path": str(db_path),
                        "schema_version": SCHEMA_VERSION,
                    })
                except Exception:
                    LOGGER.exception("Health request failed")
                    self.send_json(HTTPStatus.SERVICE_UNAVAILABLE, {"ok": False})
                finally:
                    if conn_h is not None:
                        conn_h.close()
                return

            self.send_json(HTTPStatus.NOT_FOUND, {"error": "Uç nokta bulunamadı."})

        def do_POST(self) -> None:  # noqa: N802
            parsed = urllib.parse.urlparse(self.path)

            # Database Vacuum & Optimize
            if parsed.path == "/api/system/optimize":
                conn = connect(db_path)
                try:
                    conn.execute("VACUUM")
                    conn.execute("PRAGMA optimize")
                    new_size = round(db_path.stat().st_size / 1024, 1)
                    self.send_json(HTTPStatus.OK, {
                        "status": "success",
                        "message": f"Veritabanı optimize edildi ve sıkıştırıldı. Yeni boyut: {new_size} KB",
                        "db_size_kb": new_size,
                    })
                except Exception as e:
                    self.send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(e)})
                finally:
                    conn.close()
                return

            try:
                body = read_json_body(self)
            except Exception:
                self.send_json(HTTPStatus.BAD_REQUEST, {"error": "Geçersiz JSON gövdesi."})
                return

            # Create Record
            if parsed.path == "/api/records":
                try:
                    title = body.get("title", "").strip()
                    if not title:
                        self.send_json(HTTPStatus.BAD_REQUEST, {"error": "Başlık zorunludur."})
                        return
                    media_type = body.get("media_type", "movie")
                    conn = connect(db_path)
                    try:
                        genres = body.get("genres")
                        if isinstance(genres, list):
                            genres = json.dumps(genres, ensure_ascii=False)
                        tags = body.get("tags")
                        if isinstance(tags, list):
                            tags = json.dumps(tags, ensure_ascii=False)
                        mid = add_media(
                            conn, title, media_type,
                            is_anime=bool(body.get("is_anime", False)),
                            status=body.get("status", "planned"),
                            release_year=body.get("release_year"),
                            rating=body.get("rating"),
                            note=body.get("note"),
                            tmdb_id=body.get("tmdb_id"),
                            imdb_id=body.get("imdb_id"),
                            poster_path=body.get("poster_path"),
                            overview=body.get("overview"),
                            genres=genres,
                            original_title=body.get("original_title"),
                            director=body.get("director"),
                            cast_members=body.get("cast"),
                            runtime=body.get("runtime"),
                            imdb_rating=body.get("imdb_rating"),
                            tags=tags,
                            trailer_key=body.get("trailer_key"),
                        )
                        record = fetch_media(conn, mid)
                        self.send_json(HTTPStatus.CREATED, enrich_with_poster(record) if record else {"id": mid})
                    finally:
                        conn.close()
                except Exception:
                    LOGGER.exception("Create record failed")
                    self.send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": INTERNAL_ERROR_MESSAGE})
                return

            # IMDb Search
            if parsed.path == "/api/imdb/search":
                query = body.get("query", "").strip()
                if not query:
                    self.send_json(HTTPStatus.BAD_REQUEST, {"error": "Arama sorgusu gerekli."})
                    return
                try:
                    results = imdb_search(query)
                    self.send_json(HTTPStatus.OK, {"results": results[:20]})
                except Exception:
                    LOGGER.exception("IMDb search failed")
                    self.send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "IMDb arama hatası."})
                return

            # IMDb Import
            if parsed.path.startswith("/api/imdb/import/"):
                imdb_id = parsed.path.removeprefix("/api/imdb/import/").strip()
                if not imdb_id.startswith("tt"):
                    self.send_json(HTTPStatus.BAD_REQUEST, {"error": "Geçersiz IMDb ID."})
                    return
                media_type = body.get("media_type", "movie")
                is_anime = bool(body.get("is_anime", False))
                try:
                    conn = connect(db_path)
                    try:
                        existing = conn.execute("SELECT id FROM media WHERE imdb_id = ?", (imdb_id,)).fetchone()
                        if existing:
                            record = record_payload(db_path, existing[0])
                            self.send_json(HTTPStatus.OK, {"already_exists": True, "record": record})
                            return

                        details = imdb_get_details(imdb_id, media_type=media_type)
                        poster_url = details.get("poster_url") or body.get("poster_url")

                        # Try TMDB enrichment for Turkish title/overview
                        try:
                            tmdb_match = tmdb_find_by_imdb(imdb_id, language="tr-TR")
                            if tmdb_match:
                                tr_title = tmdb_match.get("title") or tmdb_match.get("name")
                                tr_overview = tmdb_match.get("overview")
                                if tr_title and tr_title != details.get("title"):
                                    details["original_title"] = details.get("title")
                                    details["title"] = tr_title
                                if tr_overview:
                                    details["overview"] = tr_overview
                                if tmdb_match.get("poster_path") and not poster_url:
                                    poster_url = tmdb_poster_url(tmdb_match["poster_path"], "w500")
                                if tmdb_match.get("id"):
                                    details["tmdb_id"] = tmdb_match["id"]
                                    details["tmdb_rating"] = tmdb_match.get("vote_average")
                        except Exception as e:
                            LOGGER.debug("TMDB Turkish enrichment skipped: %s", e)

                        mid = import_from_imdb(conn, details, is_anime=is_anime)
                        if poster_url:
                            dest = POSTERS_DIR / f"{mid}.jpg"
                            POSTERS_DIR.mkdir(parents=True, exist_ok=True)
                            imdb_download_poster(poster_url, dest)

                        record = fetch_media(conn, mid)
                        self.send_json(HTTPStatus.CREATED, enrich_with_poster(record) if record else {"id": mid})
                    finally:
                        conn.close()
                except Exception:
                    LOGGER.exception("IMDb import failed for ID %s", imdb_id)
                    self.send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "IMDb import hatası."})
                return

            # TMDB Search
            if parsed.path == "/api/tmdb/search":
                query = body.get("query", "").strip()
                if not query:
                    self.send_json(HTTPStatus.BAD_REQUEST, {"error": "Arama sorgusu gerekli."})
                    return
                media_type = body.get("media_type", "multi")
                try:
                    if media_type == "movie":
                        data = tmdb_search_movie(query, year=body.get("year"), language="tr-TR")
                    elif media_type == "series":
                        data = tmdb_search_tv(query, year=body.get("year"), language="tr-TR")
                    else:
                        data = tmdb_search_multi(query, language="tr-TR")
                    results = [
                        tmdb_search_result_to_summary(item)
                        for item in data.get("results", [])
                        if item.get("media_type") in ("movie", "tv") or media_type != "multi"
                    ]
                    self.send_json(HTTPStatus.OK, {
                        "results": results[:20],
                        "total_results": data.get("total_results", 0),
                    })
                except Exception:
                    LOGGER.exception("TMDB search failed")
                    self.send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "TMDB arama hatası."})
                return

            # TMDB Import
            if parsed.path.startswith("/api/tmdb/import/"):
                try:
                    tmdb_id = int(parsed.path.removeprefix("/api/tmdb/import/"))
                except ValueError:
                    self.send_json(HTTPStatus.BAD_REQUEST, {"error": "Geçersiz TMDB ID."})
                    return
                media_type = body.get("media_type", "movie")
                is_anime = bool(body.get("is_anime", False))
                try:
                    conn = connect(db_path)
                    try:
                        existing = conn.execute("SELECT id FROM media WHERE tmdb_id = ?", (tmdb_id,)).fetchone()
                        if existing:
                            record = record_payload(db_path, existing[0])
                            self.send_json(HTTPStatus.OK, {"already_exists": True, "record": record})
                            return

                        if media_type == "series":
                            tmdb_data = tmdb_get_tv(tmdb_id, language="tr-TR")
                            mapped = tmdb_tv_to_media(tmdb_data)
                        else:
                            tmdb_data = tmdb_get_movie(tmdb_id, language="tr-TR")
                            mapped = tmdb_movie_to_media(tmdb_data)

                        mapped["is_anime"] = is_anime
                        mid = import_from_tmdb(conn, mapped)

                        poster_path = tmdb_data.get("poster_path")
                        if poster_path:
                            dest = POSTERS_DIR / f"{mid}.jpg"
                            POSTERS_DIR.mkdir(parents=True, exist_ok=True)
                            tmdb_download_poster(poster_path, dest)

                        record = fetch_media(conn, mid)
                        self.send_json(HTTPStatus.CREATED, enrich_with_poster(record) if record else {"id": mid})
                    finally:
                        conn.close()
                except Exception:
                    LOGGER.exception("TMDB import failed for ID %s", tmdb_id)
                    self.send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "TMDB import hatası."})
                return

            self.send_json(HTTPStatus.NOT_FOUND, {"error": "Uç nokta bulunamadı."})

        def do_PUT(self) -> None:  # noqa: N802
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path.startswith("/api/records/"):
                try:
                    media_id = int(parsed.path.removeprefix("/api/records/"))
                except ValueError:
                    self.send_json(HTTPStatus.BAD_REQUEST, {"error": "Geçersiz kayıt ID."})
                    return
                try:
                    body = read_json_body(self)
                    genres = body.get("genres")
                    if isinstance(genres, list):
                        body["genres"] = json.dumps(genres, ensure_ascii=False)
                    tags = body.get("tags")
                    if isinstance(tags, list):
                        body["tags"] = json.dumps(tags, ensure_ascii=False)
                    conn = connect(db_path)
                    try:
                        ok = update_media(conn, media_id, **body)
                        if not ok:
                            self.send_json(HTTPStatus.NOT_FOUND, {"error": "Kayıt bulunamadı."})
                            return
                        record = fetch_media(conn, media_id)
                        self.send_json(HTTPStatus.OK, enrich_with_poster(record) if record else {"id": media_id})
                    finally:
                        conn.close()
                except Exception:
                    LOGGER.exception("Update record failed")
                    self.send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": INTERNAL_ERROR_MESSAGE})
                return
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "Uç nokta bulunamadı."})

        def do_DELETE(self) -> None:  # noqa: N802
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path.startswith("/api/records/"):
                try:
                    media_id = int(parsed.path.removeprefix("/api/records/"))
                except ValueError:
                    self.send_json(HTTPStatus.BAD_REQUEST, {"error": "Geçersiz kayıt ID."})
                    return
                try:
                    conn = connect(db_path)
                    try:
                        ok = delete_media(conn, media_id)
                        if not ok:
                            self.send_json(HTTPStatus.NOT_FOUND, {"error": "Kayıt bulunamadı."})
                            return
                        poster_file = POSTERS_DIR / f"{media_id}.jpg"
                        if poster_file.is_file():
                            poster_file.unlink()
                        self.send_json(HTTPStatus.OK, {"ok": True, "deleted_id": media_id})
                    finally:
                        conn.close()
                except Exception:
                    LOGGER.exception("Delete record failed")
                    self.send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": INTERNAL_ERROR_MESSAGE})
                return
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "Uç nokta bulunamadı."})

        def log_message(self, format: str, *args: Any) -> None:
            LOGGER.info("%s - %s", self.address_string(), format % args)

    return GalleryHandler


def run_server(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, db_path_str: str | None = None) -> int:
    db_path = make_db_path(db_path_str)
    ensure_schema(db_path)
    POSTERS_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    if not TEMPLATE_PATH.is_file():
        print(f"Hata: Galeri şablonu bulunamadı: {TEMPLATE_PATH}")
        return 1

    server = ThreadingHTTPServer((host, port), make_handler(db_path))
    print(f"==================================================")
    print(f" Media Tracker — Letterboxd Tarzı Film Arşivi")
    print(f" Web UI: http://{host}:{port}")
    print(f" SQLite: {db_path} (şema v{SCHEMA_VERSION})")
    print(f"==================================================")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nSunucu kapatıldı.")
    finally:
        server.server_close()
    return 0


# =====================================================================
# 6. UNIFIED CLI ENTRYPOINT
# =====================================================================

def main() -> int:
    parser = argparse.ArgumentParser(
        prog="media-tracker",
        description="Media Tracker — Film, Dizi, Anime Arşivi ve Poster Galerisi",
    )
    parser.add_argument("--db", help="SQLite dosya yolu")
    subparsers = parser.add_subparsers(dest="command")

    # Serve Command
    serve_parser = subparsers.add_parser("serve", help="Web galeri sunucusunu başlat")
    serve_parser.add_argument("--host", default=DEFAULT_HOST, help=f"Dinleme adresi ({DEFAULT_HOST})")
    serve_parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Dinleme portu ({DEFAULT_PORT})")

    # Database Commands
    subparsers.add_parser("init", help="Veritabanını oluştur ve şemayı hazırla")
    subparsers.add_parser("reset", help="Veritabanını sıfırla (tüm verileri siler)")
    subparsers.add_parser("migrate", help="Şemayı en son sürüme güncelle")

    # List Command
    list_parser = subparsers.add_parser("list", help="Kayıtları listele")
    list_parser.add_argument("--kind", default="all", help="Medya türü (movie, series, anime, etc.)")

    # Add Command
    add_parser = subparsers.add_parser("add", help="Manuel kayıt ekle")
    add_parser.add_argument("title", help="Film/Dizi Başlığı")
    add_parser.add_argument("--type", dest="media_type", default="movie", choices=["movie", "series", "book"], help="Medya türü")
    add_parser.add_argument("--year", type=int, help="Yayın yılı")
    add_parser.add_argument("--rating", type=int, choices=range(1, 11), help="Puan (1-10)")
    add_parser.add_argument("--status", default="planned", choices=STATUSES, help="Durum")
    add_parser.add_argument("--anime", action="store_true", help="Anime olarak işaretle")

    # Fetch Posters Command
    poster_parser = subparsers.add_parser("fetch-posters", help="TMDB'den eksik posterleri indir")
    poster_parser.add_argument("--force", action="store_true", help="Mevcut posterleri yeniden indir")
    poster_parser.add_argument("--dry-run", action="store_true", help="İndirmeden nelerin yapılacağını göster")
    poster_parser.add_argument("--match-missing", action="store_true", help="TMDB ID olmayanları isimden eşleştir")

    # Export Command
    export_parser = subparsers.add_parser("export", help="Kayıtları dışa aktar")
    export_parser.add_argument("--format", default="json", choices=["json", "csv", "letterboxd"], help="Format")

    args, unknown = parser.parse_known_args()
    db_path = make_db_path(args.db)

    # Default to serve if no command provided or 'serve'
    if args.command is None or args.command == "serve":
        host = getattr(args, "host", DEFAULT_HOST)
        port = getattr(args, "port", DEFAULT_PORT)
        for i, u in enumerate(unknown):
            if u == "--host" and i + 1 < len(unknown):
                host = unknown[i + 1]
            elif u == "--port" and i + 1 < len(unknown):
                port = int(unknown[i + 1])
        return run_server(host=host, port=port, db_path_str=str(db_path))

    if args.command == "reset":
        reset_database(db_path)
        print(f"Veritabanı sıfırlandı: {db_path}")
        return 0

    ensure_schema(db_path)

    if args.command == "init":
        print(f"Veritabanı hazır: {db_path} (şema v{SCHEMA_VERSION})")
        return 0

    if args.command == "migrate":
        print(f"Şema v{SCHEMA_VERSION} — migrasyon tamamlandı: {db_path}")
        return 0

    if args.command == "list":
        conn = connect(db_path)
        where, vals = media_where(args.kind)
        rows = conn.execute(base_record_sql() + f" {where} GROUP BY m.id ORDER BY m.id DESC", vals).fetchall()
        for r in rows:
            print(f"[{r['id']}] ({r['media_type']}{'/anime' if r['is_anime'] else ''}) {r['title']} - Puan: {r['rating']} - Durum: {r['status']}")
        conn.close()
        return 0

    if args.command == "add":
        conn = connect(db_path)
        mid = add_media(conn, title=args.title, media_type=args.media_type, release_year=args.year, rating=args.rating, status=args.status, is_anime=args.anime)
        conn.close()
        print(f"Kayıt eklendi [ID #{mid}]: {args.title}")
        return 0

    if args.command == "fetch-posters":
        run_batch_fetch_posters(db_path, force=args.force, dry_run=args.dry_run, match_missing=args.match_missing)
        return 0

    if args.command == "export":
        conn = connect(db_path)
        if args.format == "letterboxd":
            print(export_records_letterboxd_csv(conn))
        elif args.format == "csv":
            print(export_records_csv(conn))
        else:
            print(export_records_json(conn))
        conn.close()
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
