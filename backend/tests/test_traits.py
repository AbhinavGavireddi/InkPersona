from app.traits import AnalysisResult, OBJECTIVE_TRAIT_GROUPS, DISCLAIMER
from app.analyzer import mock_analysis_result


def test_trait_registry_includes_core_objective_traits():
    expected = {
        "dominant_slant",
        "baseline_stability",
        "letter_spacing",
        "word_spacing",
        "pressure_estimate",
        "stroke_smoothness",
        "t_crossing_style",
        "i_dot_style",
        "legibility",
        "multiple_writers_possible",
    }
    flattened = {trait for names in OBJECTIVE_TRAIT_GROUPS.values() for trait in names}
    assert expected.issubset(flattened)
    assert len(flattened) >= 60


def test_mock_analysis_validates_full_schema_and_disclaimer():
    result = mock_analysis_result()
    assert isinstance(result, AnalysisResult)
    assert result.product_name == "InkPersona"
    assert DISCLAIMER in result.safety_review.required_disclaimer
    assert result.interpretation.confidence == "low"


def test_mock_analysis_avoids_forbidden_overclaims():
    serialized = mock_analysis_result().model_dump_json().lower()
    forbidden = [
        "diagnosis: ",
        "hire this person",
        "definitely has",
        "proves personality",
        "criminal",
        "intelligence score",
    ]
    assert all(term not in serialized for term in forbidden)
