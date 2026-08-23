#!/usr/bin/env python3
"""Media Tracker core CLI and database access layer."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
SCHEMA_FILE = ROOT / "schema.sql"
DEFAULT_DB_FILE = ROOT / "media.sqlite"
SCHEMA_VERSION = 3

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
    ]
    existing = {row[1] for row in conn.execute("PRAGMA table_info(media)").fetchall()}
    for col_name, col_type in new_columns:
        if col_name not in existing:
            conn.execute(f"ALTER TABLE media ADD COLUMN {col_name} {col_type}")

    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_media_tmdb_id "
        "ON media(tmdb_id) WHERE tmdb_id IS NOT NULL"
    )
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_media_imdb_id "
        "ON media(imdb_id) WHERE imdb_id IS NOT NULL"
    )
    conn.execute("PRAGMA user_version = 3")
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


def media_where(kind: str = "all", query: str = "", status: str | None = None) -> tuple[str, list[Any]]:
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

    if query:
        clauses.append("(m.title LIKE ? OR m.note LIKE ? OR CAST(m.release_year AS TEXT) LIKE ? OR m.director LIKE ?)")
        q_like = f"%{query}%"
        values.extend([q_like, q_like, q_like, q_like])

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
            d["genres"] = []
    elif not genres_raw:
        d["genres"] = []
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
) -> int:
    """Insert a new media record and return its generated ID."""
    cur = conn.execute(
        """
        INSERT INTO media (title, media_type, is_anime, status, release_year, rating, note,
                           tmdb_id, imdb_id, poster_path, overview, genres, original_title,
                           director, cast_members, runtime, tmdb_rating, imdb_rating)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (title.strip(), media_type, int(is_anime), status, release_year, rating, note,
         tmdb_id, imdb_id, poster_path, overview, genres, original_title,
         director, cast_members, runtime, tmdb_rating, imdb_rating),
    )
    conn.commit()
    return int(cur.lastrowid)


def update_media(conn: sqlite3.Connection, media_id: int, **fields: Any) -> bool:
    """Update specific fields of a media record. Returns True if row was found."""
    allowed = {
        "title", "media_type", "is_anime", "status", "release_year", "rating", "note",
        "tmdb_id", "imdb_id", "poster_path", "overview", "genres", "original_title",
        "director", "cast_members", "runtime", "tmdb_rating", "imdb_rating",
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
    imdb_data.pop("poster_url", None)  # Not a DB column

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


def reset_database(db_path: Path) -> None:
    """Completely wipe and recreate the database with an empty schema."""
    if db_path.is_file():
        db_path.unlink()
    # Re-apply schema
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
