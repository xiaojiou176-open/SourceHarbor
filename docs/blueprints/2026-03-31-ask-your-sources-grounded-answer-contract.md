# Ask Your Sources Grounded Answer Contract

Status: Wave 1 contract artifact

This document exists because Wave 1 ships a truthful Ask MVP, not a fake answer
layer.

Current truth:

- the repo has grounded retrieval
- the repo has knowledge cards
- the repo does not yet expose a trustworthy answer-layer API that returns
  synthesized prose with explicit citations

## Wave 1 Contract

`/ask` is allowed to:

- accept a natural-language question
- run retrieval
- show cited evidence results
- let the user jump to job trace, knowledge cards, and original sources

`/ask` is not allowed to:

- fabricate a synthesized answer
- imply that a grounded answer model already exists
- hide missing citations behind generic AI phrasing

## Future Grounded Answer Requirements

To move from search-first Ask to true answer-layer Ask, the backend must expose
an explicit contract like this:

### Request

```json
{
  "question": "What changed in the latest runs?",
  "mode": "keyword|semantic|hybrid",
  "top_k": 8,
  "filters": {
    "platform": "youtube"
  }
}
```

### Response

```json
{
  "question": "What changed in the latest runs?",
  "answer_markdown": "Grounded answer text only when enough cited evidence exists.",
  "answer_status": "grounded|insufficient_evidence|unsupported",
  "citations": [
    {
      "job_id": "uuid",
      "video_id": "uuid",
      "source": "knowledge_cards",
      "snippet": "Exact cited evidence snippet.",
      "source_url": "https://..."
    }
  ],
  "evidence_items": []
}
```

## Hallucination Guard

A future answer-layer implementation must:

- require citations for every answer
- support an `insufficient_evidence` outcome
- preserve jump links back to job trace, knowledge, and original source
- never claim hosted or external proof that is not available in current repo truth
