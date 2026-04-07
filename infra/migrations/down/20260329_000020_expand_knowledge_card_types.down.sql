-- Down migration for 20260329_000020_expand_knowledge_card_types.sql
-- Note: this rollback removes topic/claim cards before restoring the older check.

DELETE FROM knowledge_cards
WHERE card_type IN ('topic', 'claim');

ALTER TABLE knowledge_cards
    DROP CONSTRAINT IF EXISTS knowledge_cards_card_type_check;

ALTER TABLE knowledge_cards
    ADD CONSTRAINT knowledge_cards_card_type_check
    CHECK (card_type IN ('summary', 'takeaway', 'action'));
