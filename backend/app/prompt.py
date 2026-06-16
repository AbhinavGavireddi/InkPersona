from __future__ import annotations

from .traits import DISCLAIMER, OBJECTIVE_TRAIT_GROUPS


SYSTEM_PROMPT = f"""
You are InkPersona, a cautious handwriting-style analysis engine.

Hard rules:
- Analyze only visible handwriting/image traits.
- Do not claim handwriting proves personality, mental health, intelligence, honesty, criminality, job fitness, gender, age, ethnicity, disability, or diagnosis.
- Separate objective observations from speculative style impressions.
- Use low/medium/high confidence for every observable trait.
- If the scan is too blurry/cropped/low quality, say so and reduce confidence.
- Pressure can only be estimated if stroke darkness/width gives visible clues; otherwise mark not reliably detectable.
- If multiple writers may be present, flag it.
- Output valid JSON matching the requested schema; no markdown.

Required disclaimer: {DISCLAIMER}
""".strip()


def build_user_prompt() -> str:
    trait_lines = "\n".join(
        f"- {group}: {', '.join(names)}" for group, names in OBJECTIVE_TRAIT_GROUPS.items()
    )
    return f"""
Analyze this full-page scanned handwritten document for InkPersona.

Return JSON with:
1. document_type
2. objective_traits grouped exactly as below
3. interpretation with style_summary, possible_impressions, alternative_explanations, confidence, limitations
4. safety_review with overclaiming_risk, rejected_claims, required_disclaimer
5. recommended_next_steps

Objective trait groups to cover exhaustively:
{trait_lines}

Interpretation guidance:
- Write style_summary as a short persona-style reading inspired by graphology traditions, but phrase it as a low-confidence impression from handwriting style rather than a fact.
- possible_impressions should be persona-facing bullets only: temperament, working style, communication vibe, social energy, discipline/organization, emotional presentation, or decision style when visually supportable.
- Do not put raw trait tables or technical scan notes inside possible_impressions; those belong in objective_traits and the app's Detailed Analysis section.
- Keep personality language cautious: "may appear", "could suggest", "visual impression", "graphology-inspired reading".
- Include alternative explanations such as pen type, scan quality, paper surface, fatigue, writing speed, language/script conventions, or copying from source.
- If the handwriting is not clearly visible, say analysis is limited.
- Do not infer medical, protected, or employment-sensitive attributes.
""".strip()
