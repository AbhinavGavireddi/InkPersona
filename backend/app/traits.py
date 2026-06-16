from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field

Confidence = Literal["low", "medium", "high"]
Severity = Literal["none", "low", "medium", "high"]


class TraitObservation(BaseModel):
    value: str = Field(..., description="Observed value, range, or 'not reliably detectable'.")
    confidence: Confidence
    evidence: str = Field(..., description="Visible evidence from the scan; no hidden psychological claim.")


class ImageQuality(BaseModel):
    resolution: TraitObservation
    blur: TraitObservation
    contrast: TraitObservation
    lighting_evenness: TraitObservation
    skew_or_rotation: TraitObservation
    crop_completeness: TraitObservation
    background_noise: TraitObservation
    scan_artifacts: TraitObservation
    handwriting_detected: TraitObservation
    multiple_writers_possible: TraitObservation


class LayoutTraits(BaseModel):
    page_margins: TraitObservation
    margin_consistency: TraitObservation
    line_spacing: TraitObservation
    paragraph_spacing: TraitObservation
    indentation: TraitObservation
    page_density: TraitObservation
    alignment: TraitObservation
    organization: TraitObservation


class SizeAndProportionTraits(BaseModel):
    overall_letter_size: TraitObservation
    x_height: TraitObservation
    upper_zone_height: TraitObservation
    lower_zone_depth: TraitObservation
    width_to_height_ratio: TraitObservation
    size_consistency: TraitObservation
    word_height_variation: TraitObservation


class SlantAndBaselineTraits(BaseModel):
    dominant_slant: TraitObservation
    slant_consistency: TraitObservation
    baseline_direction: TraitObservation
    baseline_stability: TraitObservation
    line_waviness: TraitObservation
    terminal_line_behavior: TraitObservation


class SpacingTraits(BaseModel):
    letter_spacing: TraitObservation
    word_spacing: TraitObservation
    intra_word_spacing_consistency: TraitObservation
    inter_word_spacing_consistency: TraitObservation
    crowding_or_overlap: TraitObservation


class StrokeTraits(BaseModel):
    pressure_estimate: TraitObservation
    pressure_variation: TraitObservation
    stroke_width: TraitObservation
    stroke_smoothness: TraitObservation
    tremor_or_shakiness: TraitObservation
    speed_fluency: TraitObservation
    hesitation_marks: TraitObservation
    retracing_or_corrections: TraitObservation
    pen_lifts: TraitObservation
    starts_and_stops: TraitObservation
    ink_continuity: TraitObservation


class FormTraits(BaseModel):
    angularity_vs_roundness: TraitObservation
    connectivity: TraitObservation
    print_vs_cursive: TraitObservation
    letter_simplification: TraitObservation
    ornamentation: TraitObservation
    loop_size_and_openness: TraitObservation
    ascender_shape: TraitObservation
    descender_shape: TraitObservation
    t_crossing_style: TraitObservation
    i_dot_style: TraitObservation
    capitalization_style: TraitObservation
    punctuation_style: TraitObservation
    signature_present: TraitObservation


class ConsistencyAndLegibilityTraits(BaseModel):
    legibility: TraitObservation
    rhythm: TraitObservation
    regularity: TraitObservation
    overall_consistency: TraitObservation
    corrections_or_erasure: TraitObservation
    spelling_or_written_content_relevance: TraitObservation


class ObjectiveTraits(BaseModel):
    image_quality: ImageQuality
    layout: LayoutTraits
    size_and_proportion: SizeAndProportionTraits
    slant_and_baseline: SlantAndBaselineTraits
    spacing: SpacingTraits
    stroke: StrokeTraits
    form: FormTraits
    consistency_and_legibility: ConsistencyAndLegibilityTraits


class Interpretation(BaseModel):
    style_summary: str
    possible_impressions: list[str] = Field(default_factory=list)
    alternative_explanations: list[str] = Field(default_factory=list)
    confidence: Confidence
    limitations: list[str]


class SafetyReview(BaseModel):
    overclaiming_risk: Severity
    rejected_claims: list[str] = Field(default_factory=list)
    required_disclaimer: str


class AnalysisResult(BaseModel):
    product_name: Literal["InkPersona"] = "InkPersona"
    document_type: str
    objective_traits: ObjectiveTraits
    interpretation: Interpretation
    safety_review: SafetyReview
    recommended_next_steps: list[str]


OBJECTIVE_TRAIT_GROUPS: dict[str, list[str]] = {
    "image_quality": list(ImageQuality.model_fields.keys()),
    "layout": list(LayoutTraits.model_fields.keys()),
    "size_and_proportion": list(SizeAndProportionTraits.model_fields.keys()),
    "slant_and_baseline": list(SlantAndBaselineTraits.model_fields.keys()),
    "spacing": list(SpacingTraits.model_fields.keys()),
    "stroke": list(StrokeTraits.model_fields.keys()),
    "form": list(FormTraits.model_fields.keys()),
    "consistency_and_legibility": list(ConsistencyAndLegibilityTraits.model_fields.keys()),
}


DISCLAIMER = (
    "InkPersona analyzes visible handwriting style traits for reflection and entertainment. "
    "Handwriting alone is not a validated way to determine personality, mental health, hiring fitness, "
    "truthfulness, intelligence, or clinical traits. Treat interpretations as low-confidence impressions, "
    "not facts."
)
