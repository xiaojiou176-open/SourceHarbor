-- Revision: 20260329_000019
-- Persist digest/feed feedback as long-lived operator signals

CREATE TABLE IF NOT EXISTS feed_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL UNIQUE,
    saved BOOLEAN NOT NULL DEFAULT FALSE,
    feedback_label VARCHAR(32),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT feed_feedback_label_check
        CHECK (feedback_label IS NULL OR feedback_label IN ('useful', 'noisy', 'dismissed', 'archived')),
    CONSTRAINT fk_feed_feedback_job
        FOREIGN KEY (job_id)
        REFERENCES jobs(id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_feed_feedback_feedback_label
    ON feed_feedback(feedback_label);
