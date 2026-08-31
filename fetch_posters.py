#!/usr/bin/env python3
"""Media Tracker poster fetcher compatibility shim pointing to unified app.py."""
import sys
from app import main

if __name__ == "__main__":
    sys.argv.insert(1, "fetch-posters")
    raise SystemExit(main())
