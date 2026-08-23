#!/usr/bin/env python3
"""Media Tracker poster gallery server and API."""

from __future__ import annotations

import argparse
import json
import logging
import mimetypes
import re
import sqlite3
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import cli

ROOT = Path(__file__).resolve().parent
TEMPLATE_PATH = ROOT / "templates" / "gallery.html" if (ROOT / "templates" / "gallery.html").is_file() else ROOT / "gallery.html"
STATIC_DIR = ROOT / "static"
POSTERS_DIR = STATIC_DIR / "posters"
STATIC_URL_PREFIX = "/static/"
POSTERS_URL_PREFIX = "/static/posters/"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8766
DEFAULT_LIMIT = 50
MAX_LIMIT = 200
SERVER_VERSION = "MediaTrackerGallery/2.0"
INTERNAL_ERROR_MESSAGE = "İstek işlenirken bir hata oluştu."
LOGGER = logging.getLogger("media_tracker.gallery")

# Gallery only displays visual media — books are excluded.
GALLERY_FILTERS = ("all", "movie", "anime-movie", "series", "anime-series", "anime")
GALLERY_KINDS_SQL_EXCLUDE_BOOK = "m.media_type != 'book'"


@dataclass(frozen=True)
class QueryOptions:
    """Validated records endpoint options."""

    kind: str = "all"
    status: str | None = None
    query: str = ""
    sort: str = "updated_at"
    direction: str = "desc"
    limit: int = DEFAULT_LIMIT
    offset: int = 0

    @classmethod
    def from_params(cls: type[QueryOptions], params: dict[str, list[str]]) -> QueryOptions:
        """Construct QueryOptions from parsed query parameters."""
        kind = first_param(params, "kind", "all")
        if kind not in GALLERY_FILTERS:
            kind = "all"
        status_raw = first_param(params, "status", "")
        status = status_raw if status_raw in cli.STATUSES else None
        query = first_param(params, "q", "").strip()
        sort = first_param(params, "sort", "updated_at")
        if sort not in cli.SORT_COLUMNS:
            sort = "updated_at"
        direction = first_param(params, "dir", "desc").lower()
        if direction not in {"asc", "desc"}:
            direction = "desc"
        limit = max(1, min(parse_int_param(params, "limit", DEFAULT_LIMIT), MAX_LIMIT))
        offset = max(0, parse_int_param(params, "offset", 0))
        return cls(kind, status, query, sort, direction, limit, offset)


def first_param(params: dict[str, list[str]], name: str, default: str) -> str:
    """Retrieve the first query parameter value or return a default."""
    values = params.get(name)
    return values[0] if values else default


def parse_int_param(params: dict[str, list[str]], name: str, default: int) -> int:
    """Safely parse an integer query parameter with fallback."""
    try:
        return int(first_param(params, name, str(default)))
    except ValueError:
        return default


def db_connect(db_path: Path) -> sqlite3.Connection:
    """Open a SQLite database connection and verify schema compatibility."""
    conn = cli.connect(db_path)
    version = int(conn.execute("PRAGMA user_version").fetchone()[0])
    if version < 2:
        conn.close()
        raise RuntimeError(f"Şema sürümü uyumsuz: {version}")
    return conn


def slugify(title: str) -> str:
    """Generate a filesystem-safe slug for titles, matching fetch_posters.py logic."""
    s = re.sub(r'[\\/:*?"<>|]', "", title)
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) > 120:
        s = s[:120].rstrip()
    return s if s else "untitled"


def poster_url_for(record: dict[str, Any]) -> str | None:
    """Return the poster URL by ID if available, fall back to slug lookup, or None."""
    media_id = record.get("id")
    title = record.get("title") or ""
    # 1) ID-based file lookup
    if media_id is not None:
        by_id = POSTERS_DIR / f"{media_id}.jpg"
        if by_id.is_file():
            return f"/static/posters/{media_id}.jpg"
    # 2) Slug-based fallback lookup
    slug = slugify(str(title))
    by_slug = POSTERS_DIR / f"{slug}.jpg"
    if by_slug.is_file():
        return f"/static/posters/{slug}.jpg"
    return None


def enrich_with_poster(record: dict[str, Any]) -> dict[str, Any]:
    """Enrich a media record with poster metadata (poster_url, has_poster)."""
    url = poster_url_for(record)
    enriched = dict(record)
    enriched["poster_url"] = url
    enriched["has_poster"] = url is not None
    return enriched


def gallery_where_adjust(where: str) -> str:
    """Append the book exclusion condition to an existing SQL WHERE clause."""
    if "WHERE" in where:
        return where + f" AND {GALLERY_KINDS_SQL_EXCLUDE_BOOK}"
    return f"WHERE {GALLERY_KINDS_SQL_EXCLUDE_BOOK}"


def records_payload(db_path: Path, params: dict[str, list[str]]) -> dict[str, Any]:
    """Fetch paginated visual media records enriched with poster metadata."""
    options = QueryOptions.from_params(params)
    where, values = cli.media_where(options.kind, options.query, options.status)
    where = gallery_where_adjust(where)
    count_sql = (
        "SELECT COUNT(DISTINCT m.id) FROM media AS m "
        "LEFT JOIN book_details AS bd ON bd.media_id = m.id "
        f"{where}"
    )
    order_expr = cli.SORT_COLUMNS[options.sort]
    direction = options.direction.upper()
    data_sql = (
        cli.base_record_sql()
        + f" {where} GROUP BY m.id "
        + f"ORDER BY {order_expr} IS NULL ASC, {order_expr} {direction}, m.id ASC "
        + "LIMIT ? OFFSET ?"
    )
    conn = db_connect(db_path)
    try:
        total = int(conn.execute(count_sql, values).fetchone()[0])
        rows = conn.execute(data_sql, [*values, options.limit, options.offset]).fetchall()
        records = [enrich_with_poster(cli.row_to_record(row)) for row in rows]
        return {
            "records": records,
            "total": total,
            "limit": options.limit,
            "offset": options.offset,
            "kind": options.kind,
            "status": options.status,
            "query": options.query,
            "sort": options.sort,
            "dir": options.direction,
        }
    finally:
        conn.close()


def record_payload(db_path: Path, media_id: int) -> dict[str, Any] | None:
    """Fetch a single record with seasons and poster metadata, excluding books."""
    conn = db_connect(db_path)
    try:
        record = cli.fetch_media(conn, media_id, include_seasons=True)
        if record is None:
            return None
        if record.get("media_type") == "book":
            return None
        return enrich_with_poster(record)
    finally:
        conn.close()


def scalar(conn: sqlite3.Connection, sql: str, values: tuple[Any, ...] = (), fallback: Any = 0) -> Any:
    """Execute a query and return a single scalar value with fallback."""
    value = conn.execute(sql, values).fetchone()[0]
    return fallback if value is None else value


def summary_payload(db_path: Path) -> dict[str, Any]:
    """Generate overall visual media counts, rating distributions, and poster metrics."""
    conn = db_connect(db_path)
    try:
        counts = {
            "movie": int(scalar(conn, "SELECT COUNT(*) FROM media WHERE media_type = 'movie' AND is_anime = 0")),
            "anime-movie": int(scalar(conn, "SELECT COUNT(*) FROM media WHERE media_type = 'movie' AND is_anime = 1")),
            "series": int(scalar(conn, "SELECT COUNT(*) FROM media WHERE media_type = 'series' AND is_anime = 0")),
            "anime-series": int(scalar(conn, "SELECT COUNT(*) FROM media WHERE media_type = 'series' AND is_anime = 1")),
        }
        counts["anime"] = counts["anime-movie"] + counts["anime-series"]
        counts["all"] = sum(counts[key] for key in ("movie", "anime-movie", "series", "anime-series"))
        counts["book"] = 0
        status_counts = {
            status: int(scalar(conn, "SELECT COUNT(*) FROM media WHERE status = ? AND media_type != 'book'", (status,)))
            for status in cli.STATUSES
        }
        rating_row = conn.execute("SELECT COUNT(rating), AVG(rating) FROM media WHERE rating IS NOT NULL AND media_type != 'book'").fetchone()
        rating_count = int(rating_row[0] or 0)
        buckets = [0] * 11
        for rating, count in conn.execute(
            "SELECT rating, COUNT(*) FROM media WHERE rating IS NOT NULL AND media_type != 'book' GROUP BY rating"
        ):
            buckets[int(rating)] = int(count)
        total_pages = int(scalar(conn, "SELECT SUM(total_pages) FROM book_details"))
        read_pages = int(scalar(conn, "SELECT SUM(read_pages) FROM book_details"))
        watched_episodes = int(scalar(conn, "SELECT SUM(watched_episodes) FROM series_seasons"))
        known_total_episodes = int(scalar(conn, "SELECT SUM(episode_count) FROM series_seasons"))
        unknown_seasons = int(scalar(conn, "SELECT COUNT(*) FROM series_seasons WHERE episode_count IS NULL"))
        try:
            poster_files = list(POSTERS_DIR.glob("*.jpg"))
            id_posters = len([p for p in poster_files if p.stem.isdigit()])
        except Exception:
            id_posters = 0
            poster_files = []

        # Check if TMDB API key is configured
        tmdb_configured = False
        try:
            import tmdb as tmdb_mod
            tmdb_mod.get_api_key()
            tmdb_configured = True
        except Exception:
            pass

        return {
            "db_path": str(db_path),
            "schema_version": cli.SCHEMA_VERSION,
            "counts": counts,
            "status_counts": status_counts,
            "avg_rating": rating_row[1],
            "rating_count": rating_count,
            "rating_buckets": buckets,
            "books": {"read_pages": read_pages, "total_pages": total_pages},
            "series": {
                "watched_episodes": watched_episodes,
                "known_total_episodes": known_total_episodes,
                "unknown_seasons": unknown_seasons,
            },
            "posters": {
                "id_based": id_posters,
                "total_files": len(poster_files) if isinstance(poster_files, list) else 0,
            },
            "tmdb_configured": tmdb_configured,
        }
    finally:
        conn.close()


def json_bytes(payload: Any) -> bytes:
    """Serialize a Python object to JSON UTF-8 bytes."""
    return json.dumps(payload, ensure_ascii=False, indent=2, default=str).encode("utf-8")


def read_json_body(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    """Read and parse JSON request body."""
    length = int(handler.headers.get("Content-Length", 0))
    if length == 0:
        return {}
    raw = handler.rfile.read(length)
    return json.loads(raw.decode("utf-8"))


def static_file_path(request_path: str) -> Path | None:
    """Resolve a safe static file path within the static directory."""
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
    """Determine the MIME content type for a given file path."""
    content_type, _ = mimetypes.guess_type(path.name)
    content_type = content_type or "application/octet-stream"
    if content_type.startswith("text/") or content_type in {"application/javascript", "application/json"}:
        return f"{content_type}; charset=utf-8"
    return content_type


def make_handler(db_path: Path) -> type[BaseHTTPRequestHandler]:
    """Create an HTTP request handler bound to the given database path."""
    class GalleryHandler(BaseHTTPRequestHandler):
        server_version = SERVER_VERSION

        def send_bytes(self, status: HTTPStatus, body: bytes, content_type: str) -> None:
            self.send_response(status.value)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)

        def send_json(self, status: HTTPStatus, payload: Any) -> None:
            self.send_bytes(status, json_bytes(payload), "application/json; charset=utf-8")

        def send_file(self, status: HTTPStatus, path: Path) -> None:
            self.send_bytes(status, path.read_bytes(), file_content_type(path))

        def do_OPTIONS(self) -> None:  # noqa: N802
            """Handle CORS preflight requests."""
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query, keep_blank_values=True)
            # Serve gallery index page.
            if parsed.path in ("/", "/gallery", "/gallery/"):
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
                self.send_file(HTTPStatus.OK, logo)
                return
            if parsed.path.startswith(STATIC_URL_PREFIX):
                asset = static_file_path(parsed.path)
                if asset is None:
                    self.send_json(HTTPStatus.NOT_FOUND, {"error": "Dosya bulunamadı."})
                    return
                self.send_file(HTTPStatus.OK, asset)
                return
            if parsed.path == "/api/records":
                try:
                    self.send_json(HTTPStatus.OK, records_payload(db_path, params))
                except Exception:
                    LOGGER.exception("Records API request failed")
                    self.send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": INTERNAL_ERROR_MESSAGE})
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
                conn: sqlite3.Connection | None = None
                try:
                    conn = db_connect(db_path)
                    integrity = conn.execute("PRAGMA quick_check").fetchone()[0]
                    self.send_json(HTTPStatus.OK, {
                        "ok": integrity == "ok",
                        "db_path": str(db_path),
                        "schema_version": cli.SCHEMA_VERSION,
                    })
                except Exception:
                    LOGGER.exception("Health request failed")
                    self.send_json(HTTPStatus.SERVICE_UNAVAILABLE, {"ok": False})
                finally:
                    if conn is not None:
                        conn.close()
                return
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "Uç nokta bulunamadı."})

        def do_POST(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            try:
                body = read_json_body(self)
            except Exception:
                self.send_json(HTTPStatus.BAD_REQUEST, {"error": "Geçersiz JSON gövdesi."})
                return

            # ── Create a new record ─────────────────────────────
            if parsed.path == "/api/records":
                try:
                    title = body.get("title", "").strip()
                    if not title:
                        self.send_json(HTTPStatus.BAD_REQUEST, {"error": "Başlık zorunludur."})
                        return
                    media_type = body.get("media_type", "movie")
                    if media_type not in cli.MEDIA_TYPES:
                        self.send_json(HTTPStatus.BAD_REQUEST, {"error": f"Geçersiz medya türü: {media_type}"})
                        return
                    conn = db_connect(db_path)
                    try:
                        genres = body.get("genres")
                        if isinstance(genres, list):
                            genres = json.dumps(genres, ensure_ascii=False)
                        mid = cli.add_media(
                            conn, title, media_type,
                            is_anime=bool(body.get("is_anime", False)),
                            status=body.get("status", "planned"),
                            release_year=body.get("release_year"),
                            rating=body.get("rating"),
                            note=body.get("note"),
                            tmdb_id=body.get("tmdb_id"),
                            poster_path=body.get("poster_path"),
                            overview=body.get("overview"),
                            genres=genres,
                            original_title=body.get("original_title"),
                            runtime=body.get("runtime"),
                            tmdb_rating=body.get("tmdb_rating"),
                        )
                        # Download poster if poster_path is provided
                        if body.get("poster_path"):
                            try:
                                import tmdb as tmdb_mod
                                dest = POSTERS_DIR / f"{mid}.jpg"
                                POSTERS_DIR.mkdir(parents=True, exist_ok=True)
                                tmdb_mod.download_poster(body["poster_path"], dest)
                            except Exception as e:
                                LOGGER.warning("Poster download failed for new record %d: %s", mid, e)
                        record = cli.fetch_media(conn, mid)
                        self.send_json(HTTPStatus.CREATED, enrich_with_poster(record) if record else {"id": mid})
                    finally:
                        conn.close()
                except Exception:
                    LOGGER.exception("Create record failed")
                    self.send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": INTERNAL_ERROR_MESSAGE})
                return

            # ── TMDB Search ─────────────────────────────────────
            if parsed.path == "/api/tmdb/search":
                try:
                    import tmdb as tmdb_mod
                except ImportError:
                    self.send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "TMDB modülü yüklenemedi."})
                    return
                query = body.get("query", "").strip()
                if not query:
                    self.send_json(HTTPStatus.BAD_REQUEST, {"error": "Arama sorgusu gerekli."})
                    return
                media_type = body.get("media_type", "multi")
                try:
                    if media_type == "movie":
                        data = tmdb_mod.search_movie(query, year=body.get("year"))
                    elif media_type == "series":
                        data = tmdb_mod.search_tv(query, year=body.get("year"))
                    else:
                        data = tmdb_mod.search_multi(query)
                    results = [
                        tmdb_mod.search_result_to_summary(item)
                        for item in data.get("results", [])
                        if item.get("media_type") in ("movie", "tv") or media_type != "multi"
                    ]
                    self.send_json(HTTPStatus.OK, {
                        "results": results[:20],
                        "total_results": data.get("total_results", 0),
                    })
                except RuntimeError as e:
                    self.send_json(HTTPStatus.BAD_REQUEST, {"error": str(e)})
                except Exception:
                    LOGGER.exception("TMDB search failed")
                    self.send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "TMDB arama hatası."})
                return

            # ── TMDB Import ─────────────────────────────────────
            if parsed.path.startswith("/api/tmdb/import/"):
                try:
                    import tmdb as tmdb_mod
                except ImportError:
                    self.send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "TMDB modülü yüklenemedi."})
                    return
                try:
                    tmdb_id = int(parsed.path.removeprefix("/api/tmdb/import/"))
                except ValueError:
                    self.send_json(HTTPStatus.BAD_REQUEST, {"error": "Geçersiz TMDB ID."})
                    return
                media_type = body.get("media_type", "movie")
                is_anime = bool(body.get("is_anime", False))
                try:
                    # Check if already imported
                    conn = db_connect(db_path)
                    try:
                        existing = conn.execute("SELECT id FROM media WHERE tmdb_id = ?", (tmdb_id,)).fetchone()
                        if existing:
                            record = record_payload(db_path, existing[0])
                            self.send_json(HTTPStatus.OK, {"already_exists": True, "record": record})
                            return

                        # Fetch full details from TMDB
                        if media_type == "series":
                            tmdb_data = tmdb_mod.get_tv(tmdb_id)
                            mapped = tmdb_mod.tv_to_media(tmdb_data)
                        else:
                            tmdb_data = tmdb_mod.get_movie(tmdb_id)
                            mapped = tmdb_mod.movie_to_media(tmdb_data)

                        mapped["is_anime"] = is_anime

                        mid = cli.import_from_tmdb(conn, mapped)

                        # Download poster
                        poster_path = tmdb_data.get("poster_path")
                        if poster_path:
                            dest = POSTERS_DIR / f"{mid}.jpg"
                            POSTERS_DIR.mkdir(parents=True, exist_ok=True)
                            tmdb_mod.download_poster(poster_path, dest)

                        record = cli.fetch_media(conn, mid)
                        self.send_json(HTTPStatus.CREATED, enrich_with_poster(record) if record else {"id": mid})
                    finally:
                        conn.close()
                except Exception:
                    LOGGER.exception("TMDB import failed for ID %s", tmdb_id)
                    self.send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "TMDB import hatası."})
                return

            # ── Fetch poster for single record ──────────────────
            if parsed.path.startswith("/api/records/") and parsed.path.endswith("/fetch-poster"):
                try:
                    mid_str = parsed.path.removeprefix("/api/records/").removesuffix("/fetch-poster")
                    media_id = int(mid_str)
                except ValueError:
                    self.send_json(HTTPStatus.BAD_REQUEST, {"error": "Geçersiz kayıt ID."})
                    return
                try:
                    import tmdb as tmdb_mod
                    conn = db_connect(db_path)
                    try:
                        row = conn.execute("SELECT poster_path, title, release_year, media_type FROM media WHERE id = ?", (media_id,)).fetchone()
                        if not row:
                            self.send_json(HTTPStatus.NOT_FOUND, {"error": "Kayıt bulunamadı."})
                            return
                        poster_path = row["poster_path"]
                        if not poster_path:
                            # Try to search and match
                            mtype = row["media_type"]
                            if mtype == "movie":
                                results = tmdb_mod.search_movie(row["title"], year=row["release_year"])
                            else:
                                results = tmdb_mod.search_tv(row["title"], year=row["release_year"])
                            items = results.get("results", [])
                            if items:
                                poster_path = items[0].get("poster_path")
                                tmdb_id = items[0].get("id")
                                conn.execute("UPDATE media SET poster_path = ?, tmdb_id = ? WHERE id = ?", (poster_path, tmdb_id, media_id))
                                conn.commit()
                        if poster_path:
                            dest = POSTERS_DIR / f"{media_id}.jpg"
                            POSTERS_DIR.mkdir(parents=True, exist_ok=True)
                            tmdb_mod.download_poster(poster_path, dest, overwrite=True)
                            self.send_json(HTTPStatus.OK, {"ok": True, "poster_url": f"/static/posters/{media_id}.jpg"})
                        else:
                            self.send_json(HTTPStatus.NOT_FOUND, {"error": "Poster bulunamadı."})
                    finally:
                        conn.close()
                except Exception:
                    LOGGER.exception("Fetch poster failed")
                    self.send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "Poster indirme hatası."})
                return

            self.send_json(HTTPStatus.NOT_FOUND, {"error": "Uç nokta bulunamadı."})

        def do_PUT(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)

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
                    conn = db_connect(db_path)
                    try:
                        ok = cli.update_media(conn, media_id, **body)
                        if not ok:
                            self.send_json(HTTPStatus.NOT_FOUND, {"error": "Kayıt bulunamadı."})
                            return
                        record = cli.fetch_media(conn, media_id)
                        self.send_json(HTTPStatus.OK, enrich_with_poster(record) if record else {"id": media_id})
                    finally:
                        conn.close()
                except Exception:
                    LOGGER.exception("Update record failed")
                    self.send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": INTERNAL_ERROR_MESSAGE})
                return

            self.send_json(HTTPStatus.NOT_FOUND, {"error": "Uç nokta bulunamadı."})

        def do_DELETE(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)

            if parsed.path.startswith("/api/records/"):
                try:
                    media_id = int(parsed.path.removeprefix("/api/records/"))
                except ValueError:
                    self.send_json(HTTPStatus.BAD_REQUEST, {"error": "Geçersiz kayıt ID."})
                    return
                try:
                    conn = db_connect(db_path)
                    try:
                        ok = cli.delete_media(conn, media_id)
                        if not ok:
                            self.send_json(HTTPStatus.NOT_FOUND, {"error": "Kayıt bulunamadı."})
                            return
                        # Remove poster file if exists
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


def build_parser() -> argparse.ArgumentParser:
    """Build command-line argument parser for the gallery server."""
    parser = argparse.ArgumentParser(
        prog="media-tracker-gallery",
        description="Media Tracker poster galerisi — Letterboxd tarzı poster duvarı.",
    )
    parser.add_argument("--db", help="SQLite dosyası. Verilmezse media.sqlite kullanılır.")
    parser.add_argument("--host", default=DEFAULT_HOST, help=f"Dinleme adresi. Varsayılan: {DEFAULT_HOST}")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Dinleme portu. Varsayılan: {DEFAULT_PORT}")
    return parser


def main() -> int:
    """Entrypoint for the gallery HTTP server."""
    args = build_parser().parse_args()
    db_path = cli.make_db_path(args.db)
    cli.ensure_schema(db_path)
    POSTERS_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if not TEMPLATE_PATH.is_file():
        print(f"Hata: Galeri şablonu bulunamadı: {TEMPLATE_PATH}")
        return 1
    server = ThreadingHTTPServer((args.host, args.port), make_handler(db_path))
    print(f"Media Tracker galeri: http://{args.host}:{args.port}")
    print(f"  /          -> poster duvarı")
    print(f"  /gallery   -> poster duvarı (alias)")
    print(f"  /api/*     -> REST API (GET/POST/PUT/DELETE)")
    print(f"SQLite: {db_path} (şema v{cli.SCHEMA_VERSION})")
    poster_count = len(list(POSTERS_DIR.glob("*.jpg"))) if POSTERS_DIR.is_dir() else 0
    print(f"Poster klasörü: {POSTERS_DIR} ({poster_count} jpg)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nKapatıldı.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
