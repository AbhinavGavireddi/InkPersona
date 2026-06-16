from PIL import Image

from app import _image_to_png_bytes, analyze_for_gradio, format_report
from backend.app.analyzer import mock_analysis_result


def test_format_report_contains_persona_first_then_detailed_analysis():
    report = format_report(mock_analysis_result())
    lowered = report.lower()
    assert "inkpersona persona reading" in lowered
    assert "core persona impression" in lowered
    assert "what the handwriting may suggest" in lowered
    assert "detailed analysis" in lowered
    assert "objective trait observations" in lowered
    assert "not a validated way" in lowered
    assert lowered.index("core persona impression") < lowered.index("detailed analysis")
    assert lowered.index("detailed analysis") < lowered.index("objective trait observations")


def test_demo_analysis_returns_structured_json():
    report, payload = analyze_for_gradio(None, True)
    assert "InkPersona Persona Reading" in report
    assert payload["product_name"] == "InkPersona"
    assert "objective_traits" in payload
    assert payload["interpretation"]["confidence"] == "low"


def test_live_analysis_without_image_returns_guidance():
    report, payload = analyze_for_gradio(None, False)
    assert "Upload a handwritten scan first" in report
    assert payload == {}


def test_image_conversion_outputs_png_bytes():
    image = Image.new("RGB", (64, 64), "white")
    content = _image_to_png_bytes(image)
    assert content.startswith(b"\x89PNG")
    assert len(content) > 50
