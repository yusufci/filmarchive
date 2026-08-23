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
SCHEMA_VERSION = 2

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


def ensure_schema(db_path: Path) -> None:
    """Ensure that the database schema is applied and up to date."""
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        version_row = conn.execute("PRAGMA user_version").fetchone()
        version = int(version_row[0]) if version_row else 0
        if version == 0:
            if not SCHEMA_FILE.is_file():
                raise FileNotFoundError(f"Şema dosyası bulunamadı: {SCHEMA_FILE}")
            schema_sql = SCHEMA_FILE.read_text(encoding="utf-8")
            conn.executescript(schema_sql)
            conn.commit()
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
        clauses.append("(m.title LIKE ? OR m.note LIKE ? OR CAST(m.release_year AS TEXT) LIKE ?)")
        q_like = f"%{query}%"
        values.extend([q_like, q_like, q_like])

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
    # Ensure boolean is_anime
    d["is_anime"] = bool(d.get("is_anime", 0))
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
) -> int:
    """Insert a new media record and return its generated ID."""
    cur = conn.execute(
        """
        INSERT INTO media (title, media_type, is_anime, status, release_year, rating, note)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (title.strip(), media_type, int(is_anime), status, release_year, rating, note),
    )
    conn.commit()
    return int(cur.lastrowid)


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


def seed_sample_data(db_path: Path) -> None:
    """Seed the database with a rich set of popular movies, series, and animes."""
    ensure_schema(db_path)
    conn = connect(db_path)
    try:
        count = conn.execute("SELECT COUNT(*) FROM media").fetchone()[0]
        if count > 0:
            return  # Already has data

        samples = [
            # Movies
            ("Interstellar", "movie", False, "completed", 2014, 10, "Christopher Nolan başyapıtı. Müzikler Hans Zimmer."),
            ("Inception", "movie", False, "completed", 2010, 9, "Rüya içinde rüya mimarisi."),
            ("The Dark Knight", "movie", False, "completed", 2008, 10, "Heath Ledger Joker performansı efsane."),
            ("Fight Club", "movie", False, "completed", 1999, 9, "İlk kural: Kulüpten bahsetme."),
            ("Pulp Fiction", "movie", False, "completed", 1994, 9, "Quentin Tarantino klasiği."),
            ("Dune: Part Two", "movie", False, "completed", 2024, 9, "Görsel ve işitsel şölen."),
            ("Oppenheimer", "movie", False, "completed", 2023, 9, "Atom bombasının yaratılışı ve vicdani yükü."),
            ("The Matrix", "movie", False, "completed", 1999, 9, "Kırmızı hap mı, mavi hap mı?"),
            ("Blade Runner 2049", "movie", False, "completed", 2017, 9, "Denis Villeneuve siberpunk vizyonu."),
            ("Spider-Man: Across the Spider-Verse", "movie", False, "completed", 2023, 10, "Animasyon dünyasında devrim."),

            # Anime Movies
            ("Spirited Away", "movie", True, "completed", 2001, 10, "Hayao Miyazaki / Studio Ghibli efsanesi."),
            ("Your Name.", "movie", True, "completed", 2016, 9, "Makoto Shinkai zaman ve mekan bağı."),
            ("Princess Mononoke", "movie", True, "completed", 1997, 9, "Doğa ve insan çatışması."),
            ("A Silent Voice", "movie", True, "completed", 2016, 9, "Duygusal derinliği çok yüksek bir hikaye."),
            ("Howl's Moving Castle", "movie", True, "completed", 2004, 9, "Yürüyen Şato ve büyüleyici dünya."),

            # Series
            ("Breaking Bad", "series", False, "completed", 2008, 10, "Walter White'ın dönüşümü."),
            ("Better Call Saul", "series", False, "completed", 2015, 10, "Mükemmel sinematografi ve karakter gelişimi."),
            ("Severance", "series", False, "in_progress", 2022, 9, "Gizem dolu distopik iş ortamı."),
            ("Succession", "series", False, "completed", 2018, 9, "Roy ailesi taht kavgası."),
            ("Chernobyl", "series", False, "completed", 2019, 10, "Tarihin en iyi mini dizilerinden biri."),
            ("The Last of Us", "series", False, "in_progress", 2023, 8, "Joel ve Ellie'nin kıyamet yolculuğu."),

            # Anime Series
            ("Attack on Titan", "series", True, "completed", 2013, 10, "Shingeki no Kyojin — kusursuz kurgu."),
            ("Death Note", "series", True, "completed", 2006, 9, "Light ve L akıl oyunları."),
            ("Fullmetal Alchemist: Brotherhood", "series", True, "completed", 2009, 10, "Eşdeğer Değişim Prensibi."),
            ("Steins;Gate", "series", True, "completed", 2011, 9, "Zaman yolculuğu ve El Psy Kongroo."),
            ("Vinland Saga", "series", True, "in_progress", 2019, 9, "Thorfinn'in intikamdan bilgeliğe yolculuğu."),
            ("Cyberpunk: Edgerunners", "series", True, "completed", 2022, 9, "Studio Trigger ve Night City çılgınlığı."),
            ("Frieren: Beyond Journey's End", "series", True, "completed", 2023, 10, "Zaman, anılar ve hayatın anlamı."),
        ]

        for title, m_type, is_anime, status, year, rating, note in samples:
            mid = add_media(conn, title, m_type, is_anime, status, year, rating, note)
            if m_type == "series":
                add_series_season(conn, mid, 1, 10, 10 if status == "completed" else 5)

        conn.commit()
    finally:
        conn.close()


def main() -> int:
    """CLI tool entry point for managing media records."""
    parser = argparse.ArgumentParser(prog="media-tracker-cli", description="Media Tracker SQLite Yönetimi")
    parser.add_argument("--db", help="SQLite dosya yolu")
    subparsers = parser.add_subparsers(dest="command")

    # init / seed
    subparsers.add_parser("init", help="Veritabanını oluştur ve şemayı uygula")
    subparsers.add_parser("seed", help="Örnek verilerle veritabanını doldur")

    # list
    list_parser = subparsers.add_parser("list", help="Kayıtları listele")
    list_parser.add_argument("--kind", default="all", help="Medya türü (movie, series, anime, book)")

    args = parser.parse_args()
    db_path = make_db_path(args.db)
    ensure_schema(db_path)

    if args.command == "seed":
        seed_sample_data(db_path)
        print(f"Veritabanı örneklendirildi: {db_path}")
        return 0

    if args.command == "list":
        conn = connect(db_path)
        where, vals = media_where(args.kind)
        rows = conn.execute(base_record_sql() + f" {where} GROUP BY m.id ORDER BY m.id DESC", vals).fetchall()
        for r in rows:
            print(f"[{r['id']}] ({r['media_type']}) {r['title']} - Puan: {r['rating']} - Durum: {r['status']}")
        conn.close()
        return 0

    print("Kullanım: python cli.py [init|seed|list]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
