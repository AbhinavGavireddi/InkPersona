from __future__ import annotations

import asyncio
import io
import json

import numpy as np
from PIL import Image, ImageDraw

from backend.app import analyzer
from backend.app.config import Settings
from backend.app.preprocessing import preprocess_handwriting_image
from backend.app.prompt import build_user_prompt
from backend.app.traits import AnalysisResult


def _synthetic_handwriting_page(width: int = 1800, height: int = 900) -> bytes:
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    for idx, y in enumerate(range(180, 650, 85)):
        draw.line((260, y, 1450, y + 26 + idx * 2), fill=(25, 44, 120), width=5)
        draw.arc((300, y - 22, 390, y + 50), 5, 330, fill=(25, 44, 120), width=4)
        draw.arc((430, y - 12, 540, y + 48), 190, 20, fill=(25, 44, 120), width=4)
    # Light scan-like speckles should be removed/softened by preprocessing.
    for x in range(80, 1700, 71):
        draw.point((x, (x * 7) % height), fill=(210, 210, 210))
    buffer = io.BytesIO()
    image.rotate(3.0, expand=True, fillcolor="white").save(buffer, format="JPEG", quality=92)
    return buffer.getvalue()


def test_preprocess_handwriting_image_outputs_llm_ready_png_and_metadata():
    result = preprocess_handwriting_image(_synthetic_handwriting_page())

    assert result.content_type == "image/png"
    assert result.content.startswith(b"\x89PNG")
    assert "bilateral denoising" in result.summary
    assert "inverted Otsu binarization" in result.summary
    assert "projection metadata" in result.summary
    assert result.metadata["processed_size"][0] <= 1200
    assert result.metadata["ink_density_percent"] > 0
    assert result.metadata["estimated_line_bands"] >= 1
    assert "deskew_degrees" in result.metadata

    processed = Image.open(io.BytesIO(result.content)).convert("L")
    values = np.array(processed)
    assert values.min() < 40
    assert values.max() > 215


def test_preprocessing_crops_excess_white_margin():
    result = preprocess_handwriting_image(_synthetic_handwriting_page())
    left, top, right, bottom = result.metadata["crop_box"]

    assert left > 0
    assert top > 0
    assert right < result.metadata["original_size"][0]
    assert bottom < result.metadata["original_size"][1]


def test_prompt_includes_preprocessing_context_when_available():
    prompt = build_user_prompt("Preprocessed before vision-model analysis using crop/width normalization.")

    assert "Preprocessing applied before this image reached you" in prompt
    assert "crop/width normalization" in prompt
    assert "Do not overstate personality certainty" in prompt


def test_live_analyzer_sends_preprocessed_png_and_prompt_metadata(monkeypatch):
    captured: dict[str, object] = {}

    class FakeCompletions:
        async def create(self, **kwargs):
            captured.update(kwargs)
            payload = analyzer.mock_analysis_result().model_dump()

            class Message:
                content = json.dumps(payload)

            class Choice:
                message = Message()

            class Response:
                choices = [Choice()]

            return Response()

    class FakeChat:
        completions = FakeCompletions()

    class FakeOpenAI:
        def __init__(self, **kwargs):
            captured["client_kwargs"] = kwargs
            self.chat = FakeChat()

    monkeypatch.setattr(analyzer, "AsyncOpenAI", FakeOpenAI)
    settings = Settings(OPENAI_API_KEY="test-key")

    result = asyncio.run(analyzer.analyze_handwriting_image(_synthetic_handwriting_page(), "image/jpeg", settings))

    assert isinstance(result, AnalysisResult)
    user_content = captured["messages"][1]["content"]
    text_prompt = user_content[0]["text"]
    image_url = user_content[1]["image_url"]["url"]
    assert "Preprocessing applied before this image reached you" in text_prompt
    assert "bilateral denoising" in text_prompt
    assert image_url.startswith("data:image/png;base64,")
