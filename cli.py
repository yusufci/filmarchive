#!/usr/bin/env python3
"""Media Tracker core CLI and database access layer."""

from __future__ import annotations

import argparse
import csv
import io
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
SCHEMA_FILE = ROOT / "schema.sql"
DEFAULT_DB_FILE = ROOT / "media.sqlite"
SCHEMA_VERSION = 4

STATUSES = ("planned", "in_progress", "completed", "paused", "dropped")
MEDIA_TYPES = ("movie", "series", "book")

SORT_COLUMNS = {
    "updated_at": "m.updated_at",
    "created_at": "m.created_at",
    "title": "m.title",
    "rating": "m.rating",
    "release_year": "m.release_year",
    "status": "m.status",
    "id": "m.id",
}


def make_db_path(path_str: str | None = None) -> Path:
    """Return the resolved Path to the SQLite database."""
    if path_str:
        return Path(path_str).resolve()
    return DEFAULT_DB_FILE


def connect(db_path: Path) -> sqlite3.Connection:
    """Establish and configure a SQLite connection."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _migrate_columns(conn: sqlite3.Connection) -> None:
    """Apply schema migration — ensure all extra columns exist."""
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
    conn.execute("PRAGMA user_version = 6")
    conn.commit()


def ensure_schema(db_path: Path) -> None:
    """Ensure that the database schema is applied and up to date."""
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        version_row = conn.execute("PRAGMA user_version").fetchone()
        version = int(version_row[0]) if version_row else 0
        if version == 0:
            if not SCHEMA_FILE.is_file():
                raise FileNotFoundError(f"Sema dosyasi bulunamadi: {SCHEMA_FILE}")
            schema_sql = SCHEMA_FILE.read_text(encoding="utf-8")
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
    # Auto-generate tags from genres and flags if not explicitly provided
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
    # Watch time calculation
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

    # Top Directors
    director_counts: dict[str, int] = {}
    for row in conn.execute("SELECT director FROM media WHERE director IS NOT NULL AND director != ''"):
        for d in row[0].split(","):
            name = d.strip()
            if name:
                director_counts[name] = director_counts.get(name, 0) + 1
    top_directors = sorted(director_counts.items(), key=lambda x: x[1], reverse=True)[:8]

    # Top Cast
    cast_counts: dict[str, int] = {}
    for row in conn.execute("SELECT cast_members FROM media WHERE cast_members IS NOT NULL AND cast_members != ''"):
        for c in row[0].split(","):
            name = c.strip()
            if name:
                cast_counts[name] = cast_counts.get(name, 0) + 1
    top_cast = sorted(cast_counts.items(), key=lambda x: x[1], reverse=True)[:8]

    # Top Genres
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

    # Decade breakdown
    decade_counts: dict[str, int] = {}
    for row in conn.execute("SELECT release_year FROM media WHERE release_year IS NOT NULL"):
        year = int(row[0])
        decade = f"{(year // 10) * 10}'ler"
        decade_counts[decade] = decade_counts.get(decade, 0) + 1
    sorted_decades = sorted(decade_counts.items(), key=lambda x: x[0], reverse=True)

    # Distinct Tags
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

    # Total media counts for rates
    total_records = conn.execute("SELECT COUNT(*) FROM media").fetchone()[0] or 0
    completed_records = conn.execute("SELECT COUNT(*) FROM media WHERE status = 'completed'").fetchone()[0] or 0
    in_progress_records = conn.execute("SELECT COUNT(*) FROM media WHERE status = 'in_progress'").fetchone()[0] or 0
    planned_records = conn.execute("SELECT COUNT(*) FROM media WHERE status = 'planned'").fetchone()[0] or 0

    movie_count = conn.execute("SELECT COUNT(*) FROM media WHERE media_type = 'movie'").fetchone()[0] or 0
    series_count = conn.execute("SELECT COUNT(*) FROM media WHERE media_type = 'series'").fetchone()[0] or 0
    anime_count = conn.execute("SELECT COUNT(*) FROM media WHERE is_anime = 1").fetchone()[0] or 0

    completion_rate = round((completed_records / total_records * 100), 1) if total_records > 0 else 0.0

    # Last 30 days (1 Month) analytics
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

    # Runtime analytics
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

    # Genre total sum for percentage calculation
    total_genre_occurrences = sum(genre_counts.values()) or 1
    genre_percentages = [
        {"name": g, "count": cnt, "percent": round((cnt / total_genre_occurrences) * 100, 1)}
        for g, cnt in top_genres
    ]

    # Rating tiers percentages
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

    # Top Rated Favorites (Rating 8+)
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

    # 12-Month Watch Activity Matrix
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


def import_csv_data(conn: sqlite3.Connection, csv_text: str) -> dict[str, int]:
    """Parse Letterboxd or IMDb export CSV and import entries."""
    reader = csv.DictReader(io.StringIO(csv_text))
    imported = 0
    skipped = 0

    for row in reader:
        # Case insensitive key mapping
        clean_row = {k.strip().lower(): (v or "").strip() for k, v in row.items() if k}
        title = clean_row.get("name") or clean_row.get("title")
        if not title:
            skipped += 1
            continue

        year_val = clean_row.get("year") or clean_row.get("release date", "")[:4]
        try:
            year = int(year_val) if year_val else None
        except ValueError:
            year = None

        rating_val = clean_row.get("rating") or clean_row.get("your rating")
        try:
            rating = int(float(rating_val)) if rating_val else None
        except ValueError:
            rating = None

        # Check existing
        existing = conn.execute("SELECT id FROM media WHERE title = ? AND (release_year = ? OR ? IS NULL)", (title, year, year)).fetchone()
        if existing:
            skipped += 1
            continue

        add_media(
            conn,
            title=title,
            media_type="movie",
            is_anime=False,
            status="completed" if rating else "planned",
            release_year=year,
            rating=rating,
            note=clean_row.get("review") or clean_row.get("notes") or None,
            imdb_id=clean_row.get("const") if clean_row.get("const", "").startswith("tt") else None,
        )
        imported += 1

    return {"imported": imported, "skipped": skipped}


def reset_database(db_path: Path) -> None:
    """Completely wipe and recreate the database with an empty schema."""
    if db_path.is_file():
        db_path.unlink()
    ensure_schema(db_path)


def main() -> int:
    """CLI tool entry point for managing media records."""
    parser = argparse.ArgumentParser(prog="media-tracker-cli", description="Media Tracker SQLite Yonetimi")
    parser.add_argument("--db", help="SQLite dosya yolu")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("init", help="Veritabanini olustur ve semayi uygula")
    subparsers.add_parser("reset", help="Veritabanini sifirla (tum verileri sil)")
    subparsers.add_parser("migrate", help="Semayi en son surume guncelle")

    list_parser = subparsers.add_parser("list", help="Kayitlari listele")
    list_parser.add_argument("--kind", default="all", help="Medya turu")

    args = parser.parse_args()
    db_path = make_db_path(args.db)

    if args.command == "reset":
        reset_database(db_path)
        print(f"Veritabani sifirlandi: {db_path}")
        return 0

    ensure_schema(db_path)

    if args.command == "init":
        print(f"Veritabani hazir: {db_path}")
        return 0

    if args.command == "migrate":
        print(f"Sema v{SCHEMA_VERSION} — migration tamamlandi: {db_path}")
        return 0

    if args.command == "list":
        conn = connect(db_path)
        where, vals = media_where(args.kind)
        rows = conn.execute(base_record_sql() + f" {where} GROUP BY m.id ORDER BY m.id DESC", vals).fetchall()
        for r in rows:
            print(f"[{r['id']}] ({r['media_type']}) {r['title']} - Puan: {r['rating']} - Durum: {r['status']}")
        conn.close()
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
