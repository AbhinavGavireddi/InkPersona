from backend.app.traits import AnalysisResult, DISCLAIMER, OBJECTIVE_TRAIT_GROUPS


def _shorthand_objective_traits() -> dict[str, dict[str, str]]:
    sample_values = {
        "resolution": "high",
        "blur": "none",
        "contrast": "good",
        "handwriting_detected": "yes",
        "dominant_slant": "slight right",
        "baseline_direction": "straight",
        "pressure_estimate": "medium",
        "legibility": "high",
    }
    return {
        group: {trait: sample_values.get(trait, "medium") for trait in traits}
        for group, traits in OBJECTIVE_TRAIT_GROUPS.items()
    }


def test_analysis_result_accepts_model_shorthand_trait_strings():
    payload = {
        "product_name": "InkPersona",
        "document_type": "handwritten photo",
        "objective_traits": _shorthand_objective_traits(),
        "interpretation": {
            "style_summary": "The writing gives a controlled, organized visual impression.",
            "possible_impressions": ["may appear organized"],
            "alternative_explanations": "Variations may reflect pen, paper, scan quality, or writing speed.",
            "confidence": "moderate",
            "limitations": "Analysis is limited to visible handwriting features.",
        },
        "safety_review": {
            "overclaiming_risk": "none",
            "rejected_claims": "none",
            "required_disclaimer": DISCLAIMER,
        },
        "recommended_next_steps": "Upload another clean sample for comparison.",
    }

    result = AnalysisResult.model_validate(payload)

    assert result.objective_traits.image_quality.resolution.value == "high"
    assert result.objective_traits.image_quality.resolution.confidence == "low"
    assert "shorthand" in result.objective_traits.image_quality.resolution.evidence
    assert result.interpretation.confidence == "medium"
    assert result.interpretation.alternative_explanations == [
        "Variations may reflect pen, paper, scan quality, or writing speed."
    ]
    assert result.interpretation.limitations == ["Analysis is limited to visible handwriting features."]
    assert result.safety_review.rejected_claims == []
    assert result.recommended_next_steps == ["Upload another clean sample for comparison."]


def test_analysis_result_fills_missing_trait_evidence_and_normalizes_confidence():
    payload = {
        "value": "smooth",
        "confidence": "moderate",
    }

    from backend.app.traits import TraitObservation

    observation = TraitObservation.model_validate(payload)
    assert observation.value == "smooth"
    assert observation.confidence == "medium"
    assert "without scan-specific evidence" in observation.evidence
