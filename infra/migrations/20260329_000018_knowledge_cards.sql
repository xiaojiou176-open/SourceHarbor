-- Revision: 20260329_000018
-- Introduce structured knowledge cards derived from digest outputs

CREATE TABLE IF NOT EXISTS knowledge_cards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL,
    video_id UUID NOT NULL,
    card_type VARCHAR(32) NOT NULL,
    source_section VARCHAR(64) NOT NULL,
    title VARCHAR(255),
    body TEXT NOT NULL,
    ordinal INTEGER NOT NULL DEFAULT 0,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT knowledge_cards_card_type_check
        CHECK (card_type IN ('summary', 'takeaway', 'action')),
    CONSTRAINT knowledge_cards_ordinal_non_negative_check
        CHECK (ordinal >= 0),
    CONSTRAINT fk_knowledge_cards_job
        FOREIGN KEY (job_id)
        REFERENCES jobs(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_knowledge_cards_video
        FOREIGN KEY (video_id)
        REFERENCES videos(id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_knowledge_cards_job_id_ordinal
    ON knowledge_cards(job_id, ordinal ASC);

CREATE INDEX IF NOT EXISTS idx_knowledge_cards_video_id_created_at
    ON knowledge_cards(video_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_knowledge_cards_card_type
    ON knowledge_cards(card_type);
