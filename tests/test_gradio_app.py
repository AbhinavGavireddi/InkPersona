from PIL import Image

from app import _image_to_png_bytes, analyze_for_gradio, format_report
from backend.app.analyzer import mock_analysis_result


def test_format_report_contains_safety_boundaries():
    report = format_report(mock_analysis_result())
    lowered = report.lower()
    assert "inkpersona report" in lowered
    assert "not a validated way" in lowered
    assert "possible impressions, not facts" in lowered
    assert "objective trait observations" in lowered


def test_demo_analysis_returns_structured_json():
    report, payload = analyze_for_gradio(None, True)
    assert "InkPersona Report" in report
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
