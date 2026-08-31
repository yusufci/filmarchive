#!/usr/bin/env python3
"""Media Tracker TMDB client compatibility shim pointing to unified app.py."""
from app import (
    load_tmdb_api_key,
    get_tmdb_api_key,
    tmdb_request as _request,
    tmdb_search_movie as search_movie,
    tmdb_search_tv as search_tv,
    tmdb_search_multi as search_multi,
    tmdb_get_movie as get_movie,
    tmdb_get_tv as get_tv,
    tmdb_find_by_imdb as find_by_imdb,
    tmdb_get_random_trending as get_random_trending,
    tmdb_poster_url as poster_url,
    tmdb_download_poster as download_poster,
    tmdb_movie_to_media as movie_to_media,
    tmdb_tv_to_media as tv_to_media,
    tmdb_search_result_to_summary as search_result_to_summary,
)
