from __future__ import annotations

import asyncio
import io
import os
from pathlib import Path
from typing import Any

import gradio as gr
from dotenv import load_dotenv
from PIL import Image

from backend.app.analyzer import AnalysisError, analyze_handwriting_image, mock_analysis_result
from backend.app.config import Settings
from backend.app.traits import AnalysisResult, DISCLAIMER, OBJECTIVE_TRAIT_GROUPS

load_dotenv(Path(__file__).with_name(".env"))

APP_TITLE = "InkPersona"
APP_SUBTITLE = "AI handwriting style analysis with scientific humility."
SAFE_USE_NOTE = (
    "Do not upload sensitive documents. Images are processed by this Space runtime and, "
    "for live analysis, sent to the configured vision model provider."
)


def _settings() -> Settings:
    return Settings(
        OPENAI_API_KEY=os.getenv("OPENAI_API_KEY", ""),
        OPENAI_MODEL=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        OPENAI_TEMPERATURE=float(os.getenv("OPENAI_TEMPERATURE", "0.2")),
        OPENAI_MAX_OUTPUT_TOKENS=int(os.getenv("OPENAI_MAX_OUTPUT_TOKENS", "3500")),
    )


def _image_to_png_bytes(image: Image.Image) -> bytes:
    if not isinstance(image, Image.Image):
        raise AnalysisError("Upload a valid image first.")
    normalized = image.convert("RGB")
    buffer = io.BytesIO()
    normalized.save(buffer, format="PNG")
    return buffer.getvalue()


def _confidence_badge(confidence: str | None) -> str:
    color = {"high": "#40d48a", "medium": "#f5c451", "low": "#ff7b9c"}.get(confidence or "low", "#ff7b9c")
    return f"<span style='color:{color};font-weight:700;text-transform:uppercase'>{confidence or 'low'}</span>"


def _format_trait_group(group_name: str, observations: dict[str, Any]) -> str:
    rows = []
    for name, observation in observations.items():
        value = observation.get("value", "Not assessed")
        confidence = _confidence_badge(observation.get("confidence"))
        evidence = observation.get("evidence", "No evidence provided.")
        rows.append(
            f"| {name.replace('_', ' ').title()} | {value} | {confidence} | {evidence} |"
        )
    table = "\n".join(rows)
    return f"\n### {group_name.replace('_', ' ').title()}\n\n| Trait | Observation | Confidence | Evidence |\n|---|---:|---:|---|\n{table}\n"


def format_report(result: AnalysisResult) -> str:
    payload = result.model_dump()
    interpretation = payload["interpretation"]
    safety = payload["safety_review"]
    objective_traits = payload["objective_traits"]

    possible = "\n".join(f"- {item}" for item in interpretation.get("possible_impressions", [])) or "- No reliable impressions."
    alternatives = "\n".join(f"- {item}" for item in interpretation.get("alternative_explanations", [])) or "- Not listed."
    next_steps = "\n".join(f"- {item}" for item in payload.get("recommended_next_steps", [])) or "- Upload a clearer scan."
    rejected = "\n".join(f"- {item}" for item in safety.get("rejected_claims", [])) or "- No forbidden claims produced."
    trait_sections = "\n".join(_format_trait_group(name, traits) for name, traits in objective_traits.items())

    return f"""
# InkPersona Report

**Document type:** {payload.get('document_type', 'handwritten document')}  
**Interpretation confidence:** {_confidence_badge(interpretation.get('confidence'))}

## Style summary

{interpretation.get('style_summary', 'No summary returned.')}

## Possible impressions, not facts

{possible}

## Alternative explanations

{alternatives}

## Safety limits

{safety.get('required_disclaimer', DISCLAIMER)}

**Rejected overclaims:**

{rejected}

## Recommended next steps

{next_steps}

---

## Objective trait observations

{trait_sections}
""".strip()


def analyze_for_gradio(image: Image.Image | None, use_demo: bool) -> tuple[str, dict[str, Any]]:
    if use_demo:
        result = mock_analysis_result()
        return format_report(result), result.model_dump()

    if image is None:
        return "Upload a handwritten scan first, or enable demo mode.", {}

    settings = _settings()
    if not settings.openai_api_key or settings.openai_api_key.startswith("replace_with"):
        return (
            "OPENAI_API_KEY is not configured. Add it in Hugging Face Space Settings → Secrets, "
            "then restart the Space. You can still use demo mode locally.",
            {},
        )

    try:
        png_bytes = _image_to_png_bytes(image)
        result = asyncio.run(analyze_handwriting_image(png_bytes, "image/png", settings))
        return format_report(result), result.model_dump()
    except Exception as exc:  # noqa: BLE001 - show user-facing Gradio error
        return f"Analysis failed: {exc}", {}


def build_app() -> gr.Blocks:
    trait_count = sum(len(items) for items in OBJECTIVE_TRAIT_GROUPS.values())
    configured = bool(os.getenv("OPENAI_API_KEY")) and not os.getenv("OPENAI_API_KEY", "").startswith("replace_with")
    secret_status = "configured" if configured else "not configured"

    css = """
    .ink-hero {border: 1px solid rgba(255,255,255,.12); border-radius: 24px; padding: 24px; background: linear-gradient(135deg, rgba(126,87,255,.14), rgba(255,255,255,.04));}
    .ink-note {color: #b8b8c8; font-size: 0.95rem;}
    .ink-danger {border-left: 4px solid #f5c451; padding-left: 12px; color: #f8df8a;}
    """

    with gr.Blocks(title=APP_TITLE, css=css, theme=gr.themes.Soft(primary_hue="purple", neutral_hue="slate")) as demo:
        gr.HTML(
            f"""
            <div class='ink-hero'>
              <h1>{APP_TITLE}</h1>
              <h3>{APP_SUBTITLE}</h3>
              <p class='ink-note'>Upload a full-HD scanned handwritten page. InkPersona extracts {trait_count} objective handwriting traits before giving cautious, low-confidence style impressions.</p>
              <p class='ink-danger'>{DISCLAIMER}</p>
              <p class='ink-note'>{SAFE_USE_NOTE}</p>
              <p class='ink-note'>OpenAI secret status at launch: <strong>{secret_status}</strong></p>
            </div>
            """
        )
        with gr.Row():
            with gr.Column(scale=1):
                image = gr.Image(type="pil", label="Handwritten document scan", sources=["upload", "clipboard"])
                use_demo = gr.Checkbox(value=False, label="Use demo result instead of live OpenAI call")
                analyze = gr.Button("Analyze handwriting", variant="primary")
                gr.Markdown(
                    "**Best input:** clean, uncropped JPEG/PNG/WEBP scan at 1080p or higher. Avoid private documents during public testing."
                )
            with gr.Column(scale=2):
                report = gr.Markdown(label="Report")
                raw_json = gr.JSON(label="Structured JSON")
        analyze.click(analyze_for_gradio, inputs=[image, use_demo], outputs=[report, raw_json])
        gr.Markdown(
            "Tip: enable demo mode to verify the UI without an API key. Disable it after adding `OPENAI_API_KEY` in Hugging Face Space Secrets."
        )
    return demo


demo = build_app()

if __name__ == "__main__":
    demo.launch()
