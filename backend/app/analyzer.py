from __future__ import annotations

import base64
import json
from typing import Any
from openai import AsyncOpenAI

from app.config import Settings
from app.prompt import SYSTEM_PROMPT, build_user_prompt
from app.traits import AnalysisResult, DISCLAIMER


ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


class AnalysisError(RuntimeError):
    pass


def encode_data_url(content: bytes, content_type: str) -> str:
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise AnalysisError("Unsupported image type. Upload JPEG, PNG, or WEBP.")
    encoded = base64.b64encode(content).decode("utf-8")
    return f"data:{content_type};base64,{encoded}"


def ensure_safe_key(settings: Settings) -> str:
    key = settings.openai_api_key.strip()
    if not key or key.startswith("replace_with"):
        raise AnalysisError("OPENAI_API_KEY is not configured. Add it to .env before live analysis.")
    return key


async def analyze_handwriting_image(content: bytes, content_type: str, settings: Settings) -> AnalysisResult:
    api_key = ensure_safe_key(settings)
    data_url = encode_data_url(content, content_type)
    client = AsyncOpenAI(api_key=api_key, timeout=settings.inkpersona_request_timeout_seconds)

    response = await client.chat.completions.create(
        model=settings.openai_model,
        temperature=settings.openai_temperature,
        max_tokens=settings.openai_max_output_tokens,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": build_user_prompt()},
                    {"type": "image_url", "image_url": {"url": data_url, "detail": "high"}},
                ],
            },
        ],
    )
    raw = response.choices[0].message.content
    if not raw:
        raise AnalysisError("OpenAI returned an empty response.")
    try:
        parsed: Any = json.loads(raw)
        return AnalysisResult.model_validate(parsed)
    except Exception as exc:  # noqa: BLE001 - return useful API error
        raise AnalysisError(f"Model returned invalid analysis JSON: {exc}") from exc


def make_trait(value: str, confidence: str = "medium", evidence: str = "Mock analysis for UI testing.") -> dict[str, str]:
    return {"value": value, "confidence": confidence, "evidence": evidence}


def mock_analysis_result() -> AnalysisResult:
    trait = make_trait
    payload = {
        "product_name": "InkPersona",
        "document_type": "mock handwritten scanned page",
        "objective_traits": {
            "image_quality": {
                "resolution": trait("full-HD or higher sample assumed", "medium"),
                "blur": trait("low", "medium"),
                "contrast": trait("medium-high", "medium"),
                "lighting_evenness": trait("mostly even", "medium"),
                "skew_or_rotation": trait("minor", "medium"),
                "crop_completeness": trait("complete page visible", "medium"),
                "background_noise": trait("low", "medium"),
                "scan_artifacts": trait("none obvious", "medium"),
                "handwriting_detected": trait("yes", "high"),
                "multiple_writers_possible": trait("not indicated", "low"),
            },
            "layout": {
                "page_margins": trait("moderate"),
                "margin_consistency": trait("fairly consistent"),
                "line_spacing": trait("balanced"),
                "paragraph_spacing": trait("not enough context", "low"),
                "indentation": trait("minimal"),
                "page_density": trait("medium"),
                "alignment": trait("mostly aligned"),
                "organization": trait("structured"),
            },
            "size_and_proportion": {
                "overall_letter_size": trait("medium"),
                "x_height": trait("medium"),
                "upper_zone_height": trait("moderate"),
                "lower_zone_depth": trait("moderate"),
                "width_to_height_ratio": trait("balanced"),
                "size_consistency": trait("medium-high"),
                "word_height_variation": trait("low-medium"),
            },
            "slant_and_baseline": {
                "dominant_slant": trait("slightly right"),
                "slant_consistency": trait("medium"),
                "baseline_direction": trait("near-horizontal"),
                "baseline_stability": trait("mostly stable"),
                "line_waviness": trait("low"),
                "terminal_line_behavior": trait("slight tapering at line ends", "low"),
            },
            "spacing": {
                "letter_spacing": trait("moderate"),
                "word_spacing": trait("moderate-wide"),
                "intra_word_spacing_consistency": trait("medium"),
                "inter_word_spacing_consistency": trait("medium-high"),
                "crowding_or_overlap": trait("low"),
            },
            "stroke": {
                "pressure_estimate": trait("not reliably detectable from mock scan", "low"),
                "pressure_variation": trait("not reliably detectable", "low"),
                "stroke_width": trait("medium"),
                "stroke_smoothness": trait("smooth"),
                "tremor_or_shakiness": trait("low"),
                "speed_fluency": trait("steady"),
                "hesitation_marks": trait("few"),
                "retracing_or_corrections": trait("few"),
                "pen_lifts": trait("moderate"),
                "starts_and_stops": trait("clean"),
                "ink_continuity": trait("consistent"),
            },
            "form": {
                "angularity_vs_roundness": trait("slightly rounded"),
                "connectivity": trait("mixed print-cursive"),
                "print_vs_cursive": trait("mixed"),
                "letter_simplification": trait("moderate"),
                "ornamentation": trait("low"),
                "loop_size_and_openness": trait("moderate/open"),
                "ascender_shape": trait("simple"),
                "descender_shape": trait("moderate"),
                "t_crossing_style": trait("straight/mid-height"),
                "i_dot_style": trait("small/close", "low"),
                "capitalization_style": trait("standard"),
                "punctuation_style": trait("minimal"),
                "signature_present": trait("not visible", "low"),
            },
            "consistency_and_legibility": {
                "legibility": trait("high"),
                "rhythm": trait("steady"),
                "regularity": trait("medium-high"),
                "overall_consistency": trait("medium-high"),
                "corrections_or_erasure": trait("low"),
                "spelling_or_written_content_relevance": trait("not evaluated for personality", "low"),
            },
        },
        "interpretation": {
            "style_summary": "The handwriting visually reads as controlled, legible, and moderately spacious. This is a cautious style impression, not a personality fact.",
            "possible_impressions": ["may appear organized", "may appear deliberate", "may prefer clarity in written presentation"],
            "alternative_explanations": ["scan quality", "pen type", "writing speed", "copying from another source", "schooling or script conventions"],
            "confidence": "low",
            "limitations": [DISCLAIMER],
        },
        "safety_review": {
            "overclaiming_risk": "low",
            "rejected_claims": ["No clinical diagnosis", "No hiring suitability", "No guaranteed personality inference"],
            "required_disclaimer": DISCLAIMER,
        },
        "recommended_next_steps": ["Upload a clean, uncropped scan", "Compare with another writing sample", "Use as reflection/entertainment only"],
    }
    return AnalysisResult.model_validate(payload)
