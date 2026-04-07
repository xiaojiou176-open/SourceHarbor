-- Revision: 20260329_000020
-- Expand knowledge card types for topic and claim level assets

ALTER TABLE knowledge_cards
    DROP CONSTRAINT IF EXISTS knowledge_cards_card_type_check;

ALTER TABLE knowledge_cards
    ADD CONSTRAINT knowledge_cards_card_type_check
    CHECK (card_type IN ('summary', 'takeaway', 'action', 'topic', 'claim'));
