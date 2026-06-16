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

ROOT_DIR = Path(__file__).resolve().parent
SAMPLE_IMAGE_PATH = ROOT_DIR / "assets" / "sample-andrej-karpathy-handwriting.jpg"

load_dotenv(ROOT_DIR / ".env")

APP_TITLE = "InkPersona"
APP_SUBTITLE = "Handwriting style readings with receipts, not overclaims."
SAFE_USE_NOTE = (
    "Avoid sensitive documents during public testing. Live analysis sends the uploaded image "
    "to the configured vision model provider."
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
    color = {"high": "#047857", "medium": "#92400e", "low": "#b91c1c"}.get(confidence or "low", "#b91c1c")
    return f"<span style='color:{color};font-weight:700;text-transform:uppercase;letter-spacing:.08em'>{confidence or 'low'}</span>"


def _format_trait_group(group_name: str, observations: dict[str, Any]) -> str:
    rows = []
    for name, observation in observations.items():
        value = observation.get("value", "Not assessed")
        confidence = _confidence_badge(observation.get("confidence"))
        evidence = observation.get("evidence", "No evidence provided.")
        label = name.replace("_", " ").title()
        rows.append(f"- **{label}:** {value} · {confidence}\n  _Evidence:_ {evidence}")
    body = "\n".join(rows)
    return f"\n### {group_name.replace('_', ' ').title()}\n\n{body}\n"

def _has_live_openai_key() -> bool:
    key = os.getenv("OPENAI_API_KEY", "").strip()
    return bool(key) and not key.startswith("replace_with") and key != "placeholder"


def load_sample_image() -> tuple[Image.Image | None, bool]:
    """Load the bundled sample without forcing demo mode when live AI is configured."""
    if not SAMPLE_IMAGE_PATH.exists():
        return None, True
    with Image.open(SAMPLE_IMAGE_PATH) as image:
        sample_image = image.convert("RGB").copy()
    return sample_image, not _has_live_openai_key()


def format_report(result: AnalysisResult) -> str:
    payload = result.model_dump()
    interpretation = payload["interpretation"]
    safety = payload["safety_review"]
    objective_traits = payload["objective_traits"]

    possible = "\n".join(f"- {item}" for item in interpretation.get("possible_impressions", [])) or "- No reliable persona impressions."
    limitations = "\n".join(f"- {item}" for item in interpretation.get("limitations", [])) or f"- {DISCLAIMER}"
    alternatives = "\n".join(f"- {item}" for item in interpretation.get("alternative_explanations", [])) or "- Not listed."
    next_steps = "\n".join(f"- {item}" for item in payload.get("recommended_next_steps", [])) or "- Upload a clearer scan."
    rejected = "\n".join(f"- {item}" for item in safety.get("rejected_claims", [])) or "- No forbidden claims produced."
    trait_sections = "\n".join(_format_trait_group(name, traits) for name, traits in objective_traits.items())

    return f"""
# InkPersona Persona Reading

**Persona confidence:** {_confidence_badge(interpretation.get('confidence'))}

## Persona lens

This reads like a **graphology-inspired persona sketch** — a vibe-level reflection from the handwriting style, not a factual personality verdict.

## Core persona impression

{interpretation.get('style_summary', 'No persona summary returned.')}

## What the handwriting may suggest

{possible}

## Reading boundary

This is a graphology-inspired handwriting persona reading, not a psychological diagnosis or scientific personality test.

---

# Detailed Analysis

**Document type:** {payload.get('document_type', 'handwritten document')}

## Why this persona was inferred

The persona reading above is based on visible handwriting traits such as slant, spacing, baseline stability, letter form, rhythm, layout, legibility, and stroke behavior.

## Alternative explanations

{alternatives}

## Limitations

{limitations}

## Safety limits

{safety.get('required_disclaimer', DISCLAIMER)}

**Rejected overclaims:**

{rejected}

## Recommended next steps

{next_steps}

## Objective trait observations

{trait_sections}
""".strip()


def analyze_for_gradio(image: Image.Image | None, use_demo: bool) -> tuple[str, dict[str, Any]]:
    if use_demo:
        result = mock_analysis_result()
        return format_report(result), result.model_dump()

    if image is None:
        return "Upload a handwritten scan first, choose the sample, or enable demo mode.", {}

    settings = _settings()
    if not settings.openai_api_key or settings.openai_api_key.startswith("replace_with") or settings.openai_api_key == "placeholder":
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


def _build_css() -> str:
    return """
    :root {
      --ink-bg: #f7f4ef;
      --ink-surface: rgba(255, 255, 255, 0.86);
      --ink-line: rgba(30, 24, 18, 0.12);
      --ink-text: #1d1a17;
      --ink-muted: #6f675f;
      --ink-blue: #2747d9;
      --ink-blue-soft: rgba(39, 71, 217, 0.10);
      --ink-amber: #b87912;
      --ink-green: #0f8f68;
    }

    .gradio-container {
      max-width: 1180px !important;
      margin: 0 auto !important;
      background:
        radial-gradient(circle at top left, rgba(39, 71, 217, 0.12), transparent 34rem),
        linear-gradient(180deg, #fbfaf7 0%, var(--ink-bg) 100%) !important;
      color: var(--ink-text) !important;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif !important;
    }

    .ink-hero {
      position: relative;
      overflow: hidden;
      border: 1px solid var(--ink-line);
      border-radius: 32px;
      padding: 34px;
      margin: 8px 0 20px;
      background:
        linear-gradient(135deg, rgba(255,255,255,.94), rgba(250,247,241,.88)),
        repeating-linear-gradient(0deg, transparent 0 30px, rgba(39,71,217,.07) 31px 32px);
      box-shadow: 0 24px 70px rgba(29, 26, 23, 0.09);
    }

    .ink-hero:after {
      content: "";
      position: absolute;
      width: 230px;
      height: 230px;
      right: -80px;
      top: -70px;
      border-radius: 999px;
      background: radial-gradient(circle, rgba(39,71,217,.20), transparent 68%);
      pointer-events: none;
    }

    .ink-kicker {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      border: 1px solid var(--ink-line);
      border-radius: 999px;
      padding: 8px 12px;
      background: rgba(255,255,255,.72);
      color: var(--ink-muted);
      font-size: 13px;
      font-weight: 700;
      letter-spacing: .08em;
      text-transform: uppercase;
    }

    .ink-title {
      margin: 18px 0 10px;
      font-size: clamp(42px, 7vw, 78px);
      line-height: .9;
      letter-spacing: -0.065em;
      font-weight: 850;
      color: var(--ink-text);
    }

    .ink-title span { color: var(--ink-blue); }

    .ink-lede {
      max-width: 760px;
      color: #4a433d;
      font-size: clamp(17px, 2vw, 22px);
      line-height: 1.45;
      margin: 0;
    }

    .ink-proof-row {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 24px;
    }

    .ink-pill {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      border: 1px solid var(--ink-line);
      border-radius: 999px;
      padding: 9px 12px;
      background: rgba(255,255,255,.76);
      color: #39332e;
      font-size: 14px;
      font-weight: 650;
    }

    .ink-card {
      border: 1px solid var(--ink-line) !important;
      border-radius: 24px !important;
      padding: 18px !important;
      background: var(--ink-surface) !important;
      box-shadow: 0 16px 50px rgba(29, 26, 23, 0.06) !important;
    }

    .ink-section-title {
      margin: 0 0 8px;
      color: var(--ink-text);
      font-size: 18px;
      font-weight: 800;
      letter-spacing: -0.02em;
    }

    .ink-helper {
      color: var(--ink-muted);
      font-size: 14px;
      line-height: 1.55;
      margin: 0 0 14px;
    }

    .ink-note {
      color: var(--ink-muted);
      font-size: 13px;
      line-height: 1.55;
      border-left: 3px solid var(--ink-blue);
      padding: 10px 0 10px 12px;
      background: var(--ink-blue-soft);
      border-radius: 0 14px 14px 0;
    }

    .ink-boundary {
      margin-top: 14px;
      padding: 14px;
      border: 1px solid rgba(184,121,18,.22);
      border-radius: 18px;
      background: rgba(184,121,18,.08);
      color: #67480f;
      font-size: 13px;
      line-height: 1.55;
    }

    .ink-sample-caption {
      color: var(--ink-muted);
      font-size: 13px;
      margin-top: 8px;
    }

    #analyze-btn {
      border-radius: 16px !important;
      min-height: 48px !important;
      font-weight: 800 !important;
      background: linear-gradient(135deg, #1d3fd1, #5f35d8) !important;
      border: 0 !important;
      box-shadow: 0 14px 28px rgba(39, 71, 217, 0.25) !important;
    }

    .ink-output {
      color: var(--ink-text) !important;
    }

    .ink-output [role="tabpanel"],
    .ink-output .prose,
    .ink-output .markdown,
    .ink-output .md,
    .ink-output .contain,
    .ink-output .output-markdown {
      color: var(--ink-text) !important;
      opacity: 1 !important;
      line-height: 1.68 !important;
    }

    .ink-output p,
    .ink-output li,
    .ink-output td,
    .ink-output th {
      color: #29231e !important;
      opacity: 1 !important;
      font-size: 15px !important;
      line-height: 1.7 !important;
    }

    .ink-output h1,
    .ink-output h2,
    .ink-output h3 {
      color: #15110e !important;
      opacity: 1 !important;
      letter-spacing: -0.03em !important;
      margin-top: 1.15rem !important;
      margin-bottom: .55rem !important;
    }

    .ink-output h1 { font-size: 30px !important; }
    .ink-output h2 { font-size: 21px !important; }
    .ink-output h3 { font-size: 17px !important; color: #2747d9 !important; }

    .ink-output strong {
      color: #15110e !important;
      font-weight: 800 !important;
      opacity: 1 !important;
    }

    .ink-output em {
      color: #3d342e !important;
      opacity: 1 !important;
      font-style: italic !important;
    }

    .ink-output hr {
      border-color: rgba(30, 24, 18, 0.18) !important;
      opacity: 1 !important;
    }

    .ink-output button[role="tab"] {
      color: #5c5249 !important;
      opacity: 1 !important;
      font-weight: 750 !important;
    }

    .ink-output button[role="tab"][aria-selected="true"] {
      color: #2747d9 !important;
    }

    table {
      border-radius: 14px !important;
      overflow: hidden !important;
    }

    @media (max-width: 760px) {
      .ink-hero { padding: 24px; border-radius: 24px; }
      .ink-proof-row { gap: 8px; }
      .ink-pill { width: 100%; justify-content: center; }
    }
    """


def build_app() -> gr.Blocks:
    trait_count = sum(len(items) for items in OBJECTIVE_TRAIT_GROUPS.values())
    configured = _has_live_openai_key()
    secret_status = "Live AI ready" if configured else "Demo mode ready"
    secret_icon = "●"

    with gr.Blocks(
        title=APP_TITLE,
        css=_build_css(),
        theme=gr.themes.Soft(primary_hue="indigo", neutral_hue="slate", radius_size="lg"),
    ) as demo:
        gr.HTML(
            f"""
            <section class='ink-hero'>
              <div class='ink-kicker'>✍️ Graphology-inspired · evidence-aware</div>
              <h1 class='ink-title'>Ink<span>Persona</span></h1>
              <p class='ink-lede'>{APP_SUBTITLE} Upload a handwriting sample and get a persona-first reading backed by {trait_count} visible handwriting observations.</p>
              <div class='ink-proof-row'>
                <div class='ink-pill'>{secret_icon} {secret_status}</div>
                <div class='ink-pill'>66 objective traits</div>
                <div class='ink-pill'>Persona first, evidence below</div>
                <div class='ink-pill'>No diagnosis · no hiring claims</div>
              </div>
            </section>
            """
        )

        with gr.Row(equal_height=False):
            with gr.Column(scale=5, elem_classes=["ink-card"]):
                gr.HTML(
                    """
                    <h2 class='ink-section-title'>1. Add handwriting</h2>
                    <p class='ink-helper'>Upload a clean photo/scan, or try the built-in Andrej Karpathy note sample we tested with.</p>
                    """
                )
                image = gr.Image(
                    type="pil",
                    label="Handwritten document scan",
                    sources=["upload", "clipboard"],
                    height=310,
                )
                use_demo = gr.Checkbox(
                    value=not configured,
                    label="Use demo result instead of live LLM call",
                    info="OFF = always call the configured OpenAI vision model. ON = local static demo only; no cache or LLM call.",
                )
                sample = gr.Button("Use sample handwriting image", variant="secondary")
                gr.HTML("<p class='ink-sample-caption'>Sample: blue-ink cursive note about Andrej Karpathy and vibe-coding. Click the sample button, then Analyze handwriting.</p>")
                analyze = gr.Button("Analyze handwriting", variant="primary", elem_id="analyze-btn")
                gr.HTML(
                    f"""
                    <div class='ink-note'><strong>Best input:</strong> uncropped JPEG/PNG/WEBP, 1080p or higher. {SAFE_USE_NOTE}</div>
                    <div class='ink-boundary'><strong>Boundary:</strong> {DISCLAIMER}</div>
                    """
                )

            with gr.Column(scale=7, elem_classes=["ink-card", "ink-output"]):
                gr.HTML(
                    """
                    <h2 class='ink-section-title'>2. Read the result</h2>
                    <p class='ink-helper'>The report starts with the persona-style impression, then shows evidence, alternatives, limitations, and structured JSON.</p>
                    """
                )
                with gr.Tabs():
                    with gr.Tab("Persona report"):
                        report = gr.Markdown(label="Report")
                    with gr.Tab("Structured JSON"):
                        raw_json = gr.JSON(label="Structured JSON")
                gr.HTML(
                    "<p class='ink-sample-caption'>Tip: if the live model returns imperfect JSON, InkPersona normalizes common shorthand safely before rendering.</p>"
                )

        sample.click(load_sample_image, outputs=[image, use_demo])
        analyze.click(analyze_for_gradio, inputs=[image, use_demo], outputs=[report, raw_json])
    return demo


demo = build_app()

if __name__ == "__main__":
    demo.launch()
