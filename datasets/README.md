# InkPersona dataset notes

InkPersona should use public handwriting datasets to test objective feature extraction, not to claim personality truth.

## Strong MVP datasets for handwriting variety

1. IAM Handwriting Database
- Purpose: handwriting recognition and writer variation.
- Good for: slant, spacing, baseline, legibility, writer diversity.
- Limitation: no validated personality labels.

2. CVL Database
- Purpose: writer identification / handwriting variation.
- Good for: writer diversity and scanned-page behavior.
- Limitation: no validated personality labels.

3. RIMES
- Purpose: handwritten French documents.
- Good for: document layout and full-page multi-line analysis.
- Limitation: language/script specific, no personality labels.

4. KHATT
- Purpose: Arabic handwriting.
- Good for: avoiding Latin-only assumptions.
- Limitation: script-specific, no personality labels.

5. Bentham / READ historical handwriting collections
- Purpose: historical handwriting recognition.
- Good for: noisy scans, old ink, unusual layout.
- Limitation: not modern personality data.

## Graphology/personality-labeled leads

Public “graphology” datasets appear in community dataset sites such as Kaggle, but they are usually small, subjective, weakly documented, or based on graphology categories rather than validated psychology instruments. Use them only as exploratory prompt examples unless each dataset is audited.

Best scientific path:
- Ask users for explicit consent.
- Collect handwriting samples.
- Pair with a validated questionnaire, e.g. Big Five Inventory / IPIP style measures.
- Evaluate correlations honestly.
- Report weak/no correlations if that is what data shows.

## Required product boundary

InkPersona may say:
- “visual handwriting traits”
- “possible style impression”
- “low-confidence self-reflection”

InkPersona must not say:
- “true personality detected”
- “hire / do not hire”
- “diagnosis”
- “mental illness detected”
- “intelligence measured”
- “criminality / honesty inferred”
