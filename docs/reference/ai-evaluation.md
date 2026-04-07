# AI Evaluation

SourceHarbor keeps a small, reviewable evaluation surface in [`evals/`](../../evals/).

## Current Assets

- `evals/baseline.json`: the baseline contract and regression policy
- `evals/golden-set.sample.jsonl`: sample cases and expected signals
- `evals/README.md`: how to read the assets
- `evals/rubric.md`: what counts as passing vs regressing

## Why The Surface Is Small

This repository is source-first. The goal is to make the evaluation contract inspectable without pretending there is a giant benchmark program behind every commit.
