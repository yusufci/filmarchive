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

CREATE TRIGGER IF NOT EXISTS trg_book_details_type_insert
BEFORE INSERT ON book_details
FOR EACH ROW
WHEN NOT EXISTS (
    SELECT 1 FROM media WHERE id = NEW.media_id AND media_type = 'book' AND is_anime = 0
)
BEGIN
    SELECT RAISE(ABORT, 'book_details requires a book media record');
END;

CREATE TRIGGER IF NOT EXISTS trg_book_details_type_update
BEFORE UPDATE ON book_details
FOR EACH ROW
WHEN NOT EXISTS (
    SELECT 1 FROM media WHERE id = NEW.media_id AND media_type = 'book' AND is_anime = 0
)
BEGIN
    SELECT RAISE(ABORT, 'book_details requires a book media record');
END;

CREATE TRIGGER IF NOT EXISTS trg_series_seasons_type_insert
BEFORE INSERT ON series_seasons
FOR EACH ROW
WHEN NOT EXISTS (
    SELECT 1 FROM media WHERE id = NEW.media_id AND media_type = 'series'
)
BEGIN
    SELECT RAISE(ABORT, 'series_seasons requires a series media record');
END;

CREATE TRIGGER IF NOT EXISTS trg_series_seasons_type_update
BEFORE UPDATE ON series_seasons
FOR EACH ROW
WHEN NOT EXISTS (
    SELECT 1 FROM media WHERE id = NEW.media_id AND media_type = 'series'
)
BEGIN
    SELECT RAISE(ABORT, 'series_seasons requires a series media record');
END;

CREATE TRIGGER IF NOT EXISTS trg_media_type_guard
BEFORE UPDATE OF media_type, is_anime ON media
FOR EACH ROW
WHEN (
    (EXISTS (SELECT 1 FROM book_details WHERE media_id = OLD.id)
        AND (NEW.media_type <> 'book' OR NEW.is_anime <> 0))
    OR
    (EXISTS (SELECT 1 FROM series_seasons WHERE media_id = OLD.id)
        AND NEW.media_type <> 'series')
)
BEGIN
    SELECT RAISE(ABORT, 'media type conflicts with existing detail records');
END;

CREATE TRIGGER IF NOT EXISTS trg_book_progress_insert
AFTER INSERT ON book_details
FOR EACH ROW
BEGIN
    UPDATE media
    SET status = CASE
            WHEN status IN ('paused', 'dropped') THEN status
            WHEN NEW.read_pages = 0 THEN 'planned'
            WHEN NEW.total_pages IS NOT NULL AND NEW.read_pages = NEW.total_pages THEN 'completed'
            ELSE 'in_progress'
        END,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = NEW.media_id;
END;

CREATE TRIGGER IF NOT EXISTS trg_book_progress_update
AFTER UPDATE OF total_pages, read_pages ON book_details
FOR EACH ROW
BEGIN
    UPDATE media
    SET status = CASE
            WHEN status IN ('paused', 'dropped') THEN status
            WHEN NEW.read_pages = 0 THEN 'planned'
            WHEN NEW.total_pages IS NOT NULL AND NEW.read_pages = NEW.total_pages THEN 'completed'
            ELSE 'in_progress'
        END,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = NEW.media_id;
END;

CREATE TRIGGER IF NOT EXISTS trg_book_author_touch
AFTER UPDATE OF author ON book_details
FOR EACH ROW
BEGIN
    UPDATE media SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.media_id;
END;

CREATE TRIGGER IF NOT EXISTS trg_series_progress_insert
AFTER INSERT ON series_seasons
FOR EACH ROW
BEGIN
    UPDATE media
    SET status = CASE
            WHEN status IN ('paused', 'dropped') THEN status
            WHEN COALESCE((SELECT SUM(watched_episodes) FROM series_seasons WHERE media_id = NEW.media_id), 0) = 0
                THEN 'planned'
            WHEN NOT EXISTS (
                SELECT 1 FROM series_seasons
                WHERE media_id = NEW.media_id
                  AND (episode_count IS NULL OR watched_episodes <> episode_count)
            ) THEN 'completed'
            ELSE 'in_progress'
        END,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = NEW.media_id;
END;

CREATE TRIGGER IF NOT EXISTS trg_series_progress_update
AFTER UPDATE OF episode_count, watched_episodes ON series_seasons
FOR EACH ROW
BEGIN
    UPDATE media
    SET status = CASE
            WHEN status IN ('paused', 'dropped') THEN status
            WHEN COALESCE((SELECT SUM(watched_episodes) FROM series_seasons WHERE media_id = NEW.media_id), 0) = 0
                THEN 'planned'
            WHEN NOT EXISTS (
                SELECT 1 FROM series_seasons
                WHERE media_id = NEW.media_id
                  AND (episode_count IS NULL OR watched_episodes <> episode_count)
            ) THEN 'completed'
            ELSE 'in_progress'
        END,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = NEW.media_id;
END;

CREATE TRIGGER IF NOT EXISTS trg_series_season_number_touch
AFTER UPDATE OF season_number ON series_seasons
FOR EACH ROW
BEGIN
    UPDATE media SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.media_id;
END;

CREATE TRIGGER IF NOT EXISTS trg_series_progress_delete
AFTER DELETE ON series_seasons
FOR EACH ROW
BEGIN
    UPDATE media
    SET status = CASE
            WHEN status IN ('paused', 'dropped') THEN status
            WHEN NOT EXISTS (SELECT 1 FROM series_seasons WHERE media_id = OLD.media_id)
                THEN 'planned'
            WHEN COALESCE((SELECT SUM(watched_episodes) FROM series_seasons WHERE media_id = OLD.media_id), 0) = 0
                THEN 'planned'
            WHEN NOT EXISTS (
                SELECT 1 FROM series_seasons
                WHERE media_id = OLD.media_id
                  AND (episode_count IS NULL OR watched_episodes <> episode_count)
            ) THEN 'completed'
            ELSE 'in_progress'
        END,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = OLD.media_id;
END;

PRAGMA user_version = 2;
