#!/usr/bin/env python3
"""Fetch posters from TMDB for all media records in the database.

Usage:
    python fetch_posters.py [--db path] [--force] [--dry-run] [--match-missing]
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
import time
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import cli
import tmdb

ROOT = Path(__file__).resolve().parent
POSTERS_DIR = ROOT / "static" / "posters"


def match_and_update(conn, record: dict, dry_run: bool = False) -> str | None:
    """Try to find the TMDB entry for a record and update tmdb_id + poster_path."""
    title = record["title"]
    year = record.get("release_year")
    media_type = record["media_type"]
    media_id = record["id"]

    try:
        if media_type == "movie":
            results = tmdb.search_movie(title, year=year)
        else:
            results = tmdb.search_tv(title, year=year)
    except Exception as e:
        print(f"  [!] Arama hatasi: {e}")
        return None

    items = results.get("results", [])
    if not items:
        print(f"  [-] TMDB'de bulunamadi: {title}")
        return None

    best = items[0]
    tmdb_id = best.get("id")
    poster_path = best.get("poster_path")
    tmdb_title = best.get("title") or best.get("name") or "?"

    print(f"  -> Eslesme: {tmdb_title} (TMDB #{tmdb_id})")

    if not dry_run and tmdb_id:
        try:
            conn.execute(
                "UPDATE media SET tmdb_id = ?, poster_path = ? WHERE id = ?",
                (tmdb_id, poster_path, media_id),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            conn.execute(
                "UPDATE media SET poster_path = ? WHERE id = ?",
                (poster_path, media_id),
            )
            conn.commit()

    return poster_path


def fetch_poster_for_record(record: dict, force: bool = False) -> bool:
    """Download poster for a single record. Returns True if downloaded."""
    media_id = record["id"]
    poster_path = record.get("poster_path")

    if not poster_path:
        return False

    dest = POSTERS_DIR / f"{media_id}.jpg"
    if dest.is_file() and not force:
        return False

    return tmdb.download_poster(poster_path, dest, overwrite=force)


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="fetch-posters",
        description="TMDB'den poster görseli indir.",
    )
    parser.add_argument("--db", help="SQLite dosya yolu")
    parser.add_argument("--force", action="store_true", help="Mevcut posterleri yeniden indir")
    parser.add_argument("--dry-run", action="store_true", help="İndirmeden sadece nelerin yapılacağını göster")
    parser.add_argument("--match-missing", action="store_true", help="tmdb_id olmayan kayıtları TMDB'de ara ve eşleştir")
    args = parser.parse_args()

    db_path = cli.make_db_path(args.db)
    cli.ensure_schema(db_path)
    POSTERS_DIR.mkdir(parents=True, exist_ok=True)

    conn = cli.connect(db_path)
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

        # If no tmdb_id and --match-missing, search TMDB
        if not record.get("tmdb_id") and args.match_missing:
            print(f"{progress} Aranıyor: {title}")
            poster_path = match_and_update(conn, record, dry_run=args.dry_run)
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

        if dest.is_file() and not args.force:
            print(f"{progress} Mevcut: {title}")
            continue

        if args.dry_run:
            print(f"{progress} İndirilecek: {title} → {dest.name}")
            downloaded += 1
            continue

        print(f"{progress} Indiriliyor: {title}...", end=" ", flush=True)
        if tmdb.download_poster(record["poster_path"], dest, overwrite=args.force):
            print("[OK]")
            downloaded += 1
        else:
            print("[FAIL]")

    conn.close()

    print(f"\n{'-' * 40}")
    print(f"Toplam: {total} | Indirilen: {downloaded} | Eslesen: {matched} | Atlanan: {skipped}")

    if args.dry_run:
        print("(Dry-run modu — hiçbir dosya indirilmedi.)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
