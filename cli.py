#!/usr/bin/env python3
"""Media Tracker CLI compatibility shim pointing to unified app.py."""
import sys
from app import *
from app import main

if __name__ == "__main__":
    raise SystemExit(main())
