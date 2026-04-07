-- Down migration for 20260308_000016_content_type.sql

ALTER TABLE videos
    DROP CONSTRAINT IF EXISTS videos_content_type_check;

ALTER TABLE videos
    DROP COLUMN IF EXISTS content_type;
