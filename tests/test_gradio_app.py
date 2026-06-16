from pathlib import Path

from PIL import Image

from app import SAMPLE_IMAGE_PATH, EMPTY_REPORT, _has_live_openai_key, _image_to_png_bytes, analyze_for_gradio, build_app, format_report, load_sample_image
from backend.app.analyzer import mock_analysis_result


def test_format_report_contains_persona_first_then_detailed_analysis():
    report = format_report(mock_analysis_result())
    lowered = report.lower()
    assert "inkpersona persona reading" in lowered
    assert "persona lens" in lowered
    assert "graphology-inspired persona sketch" in lowered
    assert "core persona impression" in lowered
    assert "careful systems builder" in lowered
    assert "working-style vibe" in lowered
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


def test_sample_handwriting_image_is_available_and_readable():
    assert isinstance(SAMPLE_IMAGE_PATH, Path)
    assert SAMPLE_IMAGE_PATH.exists()
    image = Image.open(SAMPLE_IMAGE_PATH)
    assert image.format == "JPEG"
    assert image.size[0] >= 1000
    assert image.size[1] >= 400


def test_sample_button_keeps_live_llm_enabled_when_openai_key_exists(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-not-real")
    assert _has_live_openai_key() is True
    image, use_demo = load_sample_image()
    assert isinstance(image, Image.Image)
    assert use_demo is False


def test_sample_button_uses_demo_only_without_openai_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert _has_live_openai_key() is False
    image, use_demo = load_sample_image()
    assert isinstance(image, Image.Image)
    assert use_demo is True


def test_gradio_app_builds_with_clean_ui_and_sample_example():
    demo = build_app()
    config_text = str(demo.config)
    assert "InkPersona" in config_text
    assert "Load sample image" in config_text
    assert "Reading desk" in config_text
    assert "Use static demo result" in config_text
    assert "Ready for a handwriting sample" in config_text
    assert EMPTY_REPORT.startswith("# Ready")
    assert "Persona report" in config_text
    assert "Structured JSON" in config_text
