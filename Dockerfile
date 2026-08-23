FROM python:3.12-slim

LABEL maintainer="Yusuf Caymazer"
LABEL description="Media Tracker — Letterboxd tarzı kişisel film/dizi/anime takip galerisi"

WORKDIR /app

# Copy application code
COPY cli.py gallery.py tmdb.py imdb.py fetch_posters.py schema.sql ./
COPY templates/ ./templates/
COPY static/ ./static/

# Create data and poster directories
RUN mkdir -p data static/posters

# No pip dependencies — pure stdlib
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 8766

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8766/health')" || exit 1

CMD ["python", "gallery.py", "--host", "0.0.0.0", "--db", "/app/data/media.sqlite"]
