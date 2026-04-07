-- Revision: 20260329_000017
-- Introduce ingest run ledger for async poll visibility

CREATE TABLE IF NOT EXISTS ingest_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subscription_id UUID NULL,
    workflow_id VARCHAR(255) NULL UNIQUE,
    platform VARCHAR(32) NULL,
    max_new_videos INTEGER NOT NULL DEFAULT 50,
    status VARCHAR(32) NOT NULL DEFAULT 'queued',
    requested_by VARCHAR(255),
    requested_trace_id VARCHAR(255),
    filters_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    jobs_created INTEGER NOT NULL DEFAULT 0,
    candidates_count INTEGER NOT NULL DEFAULT 0,
    feeds_polled INTEGER NOT NULL DEFAULT 0,
    entries_fetched INTEGER NOT NULL DEFAULT 0,
    entries_normalized INTEGER NOT NULL DEFAULT 0,
    ingest_events_created INTEGER NOT NULL DEFAULT 0,
    ingest_event_duplicates INTEGER NOT NULL DEFAULT 0,
    job_duplicates INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ingest_runs_status_check
        CHECK (status IN ('queued', 'running', 'succeeded', 'failed', 'skipped')),
    CONSTRAINT ingest_runs_non_negative_counts_check
        CHECK (
            jobs_created >= 0
            AND candidates_count >= 0
            AND feeds_polled >= 0
            AND entries_fetched >= 0
            AND entries_normalized >= 0
            AND ingest_events_created >= 0
            AND ingest_event_duplicates >= 0
            AND job_duplicates >= 0
        ),
    CONSTRAINT fk_ingest_runs_subscription
        FOREIGN KEY (subscription_id)
        REFERENCES subscriptions(id)
        ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS ingest_run_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ingest_run_id UUID NOT NULL,
    subscription_id UUID NULL,
    video_id UUID NULL,
    job_id UUID NULL,
    ingest_event_id UUID NULL,
    platform VARCHAR(32) NOT NULL,
    video_uid VARCHAR(512) NOT NULL,
    source_url VARCHAR(2048) NOT NULL,
    title VARCHAR(500),
    published_at TIMESTAMPTZ,
    entry_hash VARCHAR(128),
    pipeline_mode VARCHAR(64),
    content_type VARCHAR(32) NOT NULL DEFAULT 'video',
    item_status VARCHAR(32) NOT NULL DEFAULT 'queued',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ingest_run_items_item_status_check
        CHECK (item_status IN ('queued', 'deduped', 'skipped')),
    CONSTRAINT ingest_run_items_content_type_check
        CHECK (content_type IN ('video', 'article')),
    CONSTRAINT fk_ingest_run_items_ingest_run
        FOREIGN KEY (ingest_run_id)
        REFERENCES ingest_runs(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_ingest_run_items_subscription
        FOREIGN KEY (subscription_id)
        REFERENCES subscriptions(id)
        ON DELETE SET NULL,
    CONSTRAINT fk_ingest_run_items_video
        FOREIGN KEY (video_id)
        REFERENCES videos(id)
        ON DELETE SET NULL,
    CONSTRAINT fk_ingest_run_items_job
        FOREIGN KEY (job_id)
        REFERENCES jobs(id)
        ON DELETE SET NULL,
    CONSTRAINT fk_ingest_run_items_ingest_event
        FOREIGN KEY (ingest_event_id)
        REFERENCES ingest_events(id)
        ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_ingest_runs_status_created_at
    ON ingest_runs(status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_ingest_runs_platform_created_at
    ON ingest_runs(platform, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_ingest_run_items_run_id_created_at
    ON ingest_run_items(ingest_run_id, created_at ASC);

CREATE INDEX IF NOT EXISTS idx_ingest_run_items_job_id
    ON ingest_run_items(job_id);
