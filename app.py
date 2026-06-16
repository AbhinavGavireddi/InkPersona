from __future__ import annotations

import asyncio
import io
import json
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
EMPTY_REPORT = """
# Ready for a handwriting sample

Load the sample image or upload a clean page. The reading will appear here in three layers:

- Persona sketch: the first-pass handwriting impression
- Evidence: visible traits such as spacing, baseline, rhythm, slant, and form
- Boundaries: alternative explanations and claims InkPersona refuses to make

Use static demo for a quick UI preview. Turn it off when an OpenAI key is configured to call the live vision model.
""".strip()


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


def _json_for_display(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False) if payload else "{}"


def analyze_for_gradio(image: Image.Image | None, use_demo: bool) -> tuple[str, str]:
    if use_demo:
        result = mock_analysis_result()
        payload = result.model_dump()
        return format_report(result), _json_for_display(payload)

    if image is None:
        return "Upload a handwritten scan first, choose the sample, or enable demo mode.", "{}"

    settings = _settings()
    if not settings.openai_api_key or settings.openai_api_key.startswith("replace_with") or settings.openai_api_key == "placeholder":
        return (
            "OPENAI_API_KEY is not configured. Add it in Hugging Face Space Settings → Secrets, "
            "then restart the Space. You can still use demo mode locally.",
            "{}",
        )

    try:
        png_bytes = _image_to_png_bytes(image)
        result = asyncio.run(analyze_handwriting_image(png_bytes, "image/png", settings))
        payload = result.model_dump()
        return format_report(result), _json_for_display(payload)
    except Exception as exc:  # noqa: BLE001 - show user-facing Gradio error
        return f"Analysis failed: {exc}", "{}"


def _build_css() -> str:
    return """
    :root {
      --ink-paper: #f5f2ec;
      --ink-panel: #fffdf8;
      --ink-panel-2: #fbf7ef;
      --ink-rule: rgba(36, 30, 24, 0.14);
      --ink-rule-strong: rgba(36, 30, 24, 0.24);
      --ink-text: #191612;
      --ink-muted: #696055;
      --ink-faint: #968d82;
      --ink-blue: #193bd1;
      --ink-blue-dark: #10247a;
      --ink-blue-wash: rgba(25, 59, 209, 0.075);
      --ink-green: #0b6f4f;
      --ink-amber: #8f5b08;
      --ink-red: #9f1d1d;
      --ink-shadow: 0 20px 80px rgba(32, 25, 17, 0.08);
    }

    .gradio-container {
      max-width: 1760px !important;
      width: calc(100vw - 28px) !important;
      min-height: 100vh !important;
      margin: 0 auto !important;
      padding: 14px !important;
      background:
        linear-gradient(90deg, rgba(25, 59, 209, 0.035) 1px, transparent 1px),
        linear-gradient(180deg, rgba(25, 59, 209, 0.035) 1px, transparent 1px),
        var(--ink-paper) !important;
      background-size: 32px 32px, 32px 32px, auto !important;
      color: var(--ink-text) !important;
      font-family: ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", Inter, Helvetica, Arial, sans-serif !important;
    }

    .main,
    .wrap,
    .contain,
    .gradio-container > .contain {
      max-width: none !important;
      width: 100% !important;
    }

    .ink-shell {
      display: grid !important;
      grid-template-columns: minmax(280px, 0.72fr) minmax(520px, 1.65fr) !important;
      gap: 16px;
      min-height: calc(100vh - 34px);
      align-items: stretch;
      overflow: hidden;
    }

    .ink-shell > *,
    .ink-grid > *,
    .ink-brand-panel,
    .ink-work-panel,
    .ink-card,
    .ink-output,
    .ink-output-card {
      min-width: 0 !important;
      max-width: 100% !important;
      box-sizing: border-box !important;
    }

    .ink-brand-panel,
    .ink-work-panel {
      border: 1px solid var(--ink-rule) !important;
      background: rgba(255, 253, 248, 0.92) !important;
      box-shadow: var(--ink-shadow) !important;
      backdrop-filter: blur(16px);
    }

    .ink-brand-panel {
      border-radius: 28px !important;
      padding: 22px !important;
      position: sticky;
      top: 14px;
      min-height: calc(100vh - 34px);
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      overflow: hidden;
    }

    .ink-brand-panel:before {
      content: "";
      position: absolute;
      inset: 12px;
      border-radius: 22px;
      border: 1px solid rgba(25, 59, 209, 0.10);
      pointer-events: none;
    }

    .ink-brand-mark {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      color: var(--ink-muted);
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 11px;
      letter-spacing: .14em;
      text-transform: uppercase;
      position: relative;
      z-index: 1;
    }

    .ink-live-dot {
      width: 8px;
      height: 8px;
      border-radius: 999px;
      background: var(--ink-green);
      box-shadow: 0 0 0 4px rgba(11, 111, 79, 0.12);
      display: inline-block;
      margin-right: 8px;
    }

    .ink-title {
      position: relative;
      z-index: 1;
      margin: 52px 0 16px;
      max-width: 560px;
      color: var(--ink-text);
      font-family: ui-serif, Georgia, Cambria, "Times New Roman", Times, serif;
      font-size: clamp(52px, 8.2vw, 128px);
      line-height: .82;
      letter-spacing: -0.075em;
      font-weight: 540;
    }

    .ink-title span {
      display: block;
      color: var(--ink-blue);
      font-style: italic;
      transform: translateX(.08em);
    }

    .ink-lede {
      position: relative;
      z-index: 1;
      max-width: 610px;
      color: #443b32;
      font-size: clamp(16px, 1.45vw, 21px);
      line-height: 1.5;
      letter-spacing: -0.015em;
      margin: 0;
    }

    .ink-proof-grid {
      position: relative;
      z-index: 1;
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1px;
      border: 1px solid var(--ink-rule);
      background: var(--ink-rule);
      border-radius: 20px;
      overflow: hidden;
      margin-top: 30px;
    }

    .ink-proof-cell {
      min-height: 82px;
      padding: 14px;
      background: rgba(255, 253, 248, 0.74);
    }

    .ink-proof-label {
      color: var(--ink-faint);
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 10px;
      letter-spacing: .14em;
      text-transform: uppercase;
      margin-bottom: 8px;
    }

    .ink-proof-value {
      color: var(--ink-text);
      font-size: 15px;
      font-weight: 760;
      line-height: 1.25;
    }

    .ink-specimen-rail {
      position: relative;
      z-index: 1;
      margin-top: 28px;
      border-top: 1px solid var(--ink-rule);
      padding-top: 18px;
      display: grid;
      grid-template-columns: 54px 1fr;
      gap: 14px;
      align-items: start;
    }

    .ink-specimen-index {
      height: 54px;
      border: 1px solid var(--ink-rule-strong);
      border-radius: 999px;
      display: grid;
      place-items: center;
      color: var(--ink-blue);
      font-family: ui-serif, Georgia, serif;
      font-size: 22px;
      font-style: italic;
      background: var(--ink-blue-wash);
    }

    .ink-specimen-copy {
      color: var(--ink-muted);
      font-size: 13px;
      line-height: 1.55;
      margin: 0;
    }

    .ink-work-panel {
      border-radius: 28px !important;
      padding: 14px !important;
      min-height: calc(100vh - 34px);
    }

    .ink-grid {
      display: grid !important;
      grid-template-columns: minmax(310px, .52fr) minmax(0, 1fr) !important;
      gap: 14px !important;
      min-height: auto;
      align-items: start !important;
    }

    .ink-card {
      border: 1px solid var(--ink-rule) !important;
      border-radius: 22px !important;
      padding: 18px !important;
      background: rgba(255, 253, 248, 0.78) !important;
      box-shadow: none !important;
    }

    .ink-output-card {
      min-height: calc(100vh - 92px);
    }

    .ink-input-card {
      display: flex;
      flex-direction: column;
      gap: 10px !important;
      min-height: auto;
    }

    .ink-output-card {
      display: flex;
      flex-direction: column;
      min-height: calc(100vh - 92px);
      background:
        linear-gradient(90deg, rgba(25,59,209,.055) 1px, transparent 1px),
        var(--ink-panel) !important;
      background-size: 28px 28px, auto !important;
    }

    .ink-section-title {
      margin: 0 0 6px;
      color: var(--ink-text);
      font-family: ui-serif, Georgia, Cambria, serif;
      font-size: 25px;
      font-weight: 520;
      letter-spacing: -0.035em;
    }

    .ink-helper {
      color: var(--ink-muted);
      font-size: 14px;
      line-height: 1.55;
      margin: 0 0 16px;
    }

    .ink-note,
    .ink-boundary {
      color: #4c4238;
      font-size: 12.5px;
      line-height: 1.5;
      padding: 12px 13px;
      border: 1px solid var(--ink-rule);
      border-radius: 16px;
      background: rgba(251, 247, 239, 0.82);
    }

    .ink-boundary {
      margin-top: 10px;
      border-color: rgba(143, 91, 8, 0.22);
      background: rgba(143, 91, 8, 0.07);
      color: #5a3d0b;
    }

    .ink-sample-caption {
      color: var(--ink-muted);
      font-size: 12.5px;
      line-height: 1.45;
      margin-top: 8px;
    }

    .ink-mode-strip {
      display: grid;
      grid-template-columns: 1fr;
      gap: 8px;
      margin: 14px 0;
    }

    .ink-actions {
      display: grid !important;
      grid-template-columns: minmax(0, 1fr) minmax(0, 1.1fr) !important;
      gap: 10px !important;
      align-items: stretch !important;
      margin-top: 2px !important;
    }

    .ink-actions button {
      min-height: 42px !important;
      width: 100% !important;
      border-radius: 13px !important;
      font-size: 14px !important;
      font-weight: 760 !important;
      padding: 0 12px !important;
      white-space: nowrap !important;
    }

    #analyze-btn {
      min-height: 42px !important;
      background: #191612 !important;
      border: 1px solid #191612 !important;
      color: #fffdf8 !important;
      box-shadow: 0 10px 20px rgba(25, 22, 18, 0.14) !important;
    }

    #analyze-btn:hover {
      background: var(--ink-blue) !important;
      border-color: var(--ink-blue) !important;
    }

    button.secondary,
    .secondary button {
      border-radius: 14px !important;
    }

    .ink-output {
      color: var(--ink-text) !important;
    }

    .ink-output [role="tabpanel"] {
      min-height: calc(100vh - 224px) !important;
      overflow: auto !important;
      padding-right: 8px !important;
      max-width: 100% !important;
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
      max-width: 74ch !important;
      overflow-wrap: anywhere !important;
      word-break: normal !important;
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
      letter-spacing: -0.035em !important;
      margin-top: 1.05rem !important;
      margin-bottom: .55rem !important;
    }

    .ink-output h1 {
      font-family: ui-serif, Georgia, Cambria, serif !important;
      font-size: 34px !important;
      font-weight: 520 !important;
    }
    .ink-output h2 { font-size: 20px !important; }
    .ink-output h3 { font-size: 16px !important; color: var(--ink-blue-dark) !important; }

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
      border-radius: 12px !important;
    }

    .ink-output button[role="tab"][aria-selected="true"] {
      color: var(--ink-blue) !important;
      background: var(--ink-blue-wash) !important;
    }

    .image-container,
    .image-frame,
    .image-preview {
      border-radius: 16px !important;
    }

    table {
      border-radius: 14px !important;
      overflow: hidden !important;
    }

    @media (max-width: 1180px) {
      .gradio-container { width: calc(100vw - 16px) !important; padding: 8px !important; }
      .ink-shell { grid-template-columns: 1fr; }
      .ink-brand-panel { position: relative; top: 0; min-height: auto; }
      .ink-title { margin-top: 30px; font-size: clamp(54px, 13vw, 98px); }
      .ink-work-panel { min-height: auto; }
      .ink-grid { grid-template-columns: 1fr !important; min-height: auto; }
      .ink-input-card, .ink-output-card { min-height: auto; }
      .ink-output [role="tabpanel"] { min-height: 520px !important; }
    }

    @media (max-width: 720px) {
      .ink-brand-panel, .ink-work-panel { border-radius: 20px !important; padding: 14px !important; }
      .ink-proof-grid { grid-template-columns: 1fr; }
      .ink-specimen-rail { grid-template-columns: 42px 1fr; }
      .ink-specimen-index { width: 42px; height: 42px; font-size: 18px; }
      .ink-card { border-radius: 18px !important; padding: 14px !important; }
      .ink-section-title { font-size: 22px; }
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
        with gr.Row(equal_height=False, elem_classes=["ink-shell"]):
            with gr.Column(scale=3, elem_classes=["ink-brand-panel"]):
                gr.HTML(
                    f"""
                    <div class='ink-brand-mark'>
                      <span>InkPersona / handwriting lab</span>
                      <span><i class='ink-live-dot'></i>{secret_status}</span>
                    </div>
                    <div>
                      <h1 class='ink-title'>Ink<span>Persona</span></h1>
                      <p class='ink-lede'>A quieter handwriting-reading desk: upload a sample, get a persona-style interpretation first, then inspect the visible traits behind it.</p>
                      <div class='ink-proof-grid'>
                        <div class='ink-proof-cell'>
                          <div class='ink-proof-label'>Mode</div>
                          <div class='ink-proof-value'>{secret_icon} {secret_status}</div>
                        </div>
                        <div class='ink-proof-cell'>
                          <div class='ink-proof-label'>Coverage</div>
                          <div class='ink-proof-value'>{trait_count} visible handwriting traits</div>
                        </div>
                        <div class='ink-proof-cell'>
                          <div class='ink-proof-label'>Output</div>
                          <div class='ink-proof-value'>Persona first, evidence below</div>
                        </div>
                        <div class='ink-proof-cell'>
                          <div class='ink-proof-label'>Boundary</div>
                          <div class='ink-proof-value'>No diagnosis · no hiring claims</div>
                        </div>
                      </div>
                    </div>
                    <div class='ink-specimen-rail'>
                      <div class='ink-specimen-index'>Aa</div>
                      <p class='ink-specimen-copy'>{APP_SUBTITLE} Designed as a reading desk, not a chatbot page: document on the left, report on the right, evidence always within reach.</p>
                    </div>
                    """
                )

            with gr.Column(scale=9, elem_classes=["ink-work-panel"]):
                with gr.Row(equal_height=True, elem_classes=["ink-grid"]):
                    with gr.Column(scale=4, elem_classes=["ink-card", "ink-input-card"]):
                        gr.HTML(
                            """
                            <h2 class='ink-section-title'>Add handwriting</h2>
                            <p class='ink-helper'>Use a clean page photo or the built-in Andrej Karpathy sample. The live/demo switch below makes the model path explicit.</p>
                            """
                        )
                        image = gr.Image(
                            type="pil",
                            label="Handwritten document scan",
                            sources=["upload"],
                            height=220,
                        )
                        use_demo = gr.Checkbox(
                            value=not configured,
                            label="Use static demo result",
                            info="Off calls the configured OpenAI vision model. On uses the local demo only; no cache, no LLM call.",
                        )
                        with gr.Row(equal_height=True, elem_classes=["ink-actions"]):
                            sample = gr.Button("Load sample", variant="secondary")
                            analyze = gr.Button("Read handwriting", variant="primary", elem_id="analyze-btn")
                        gr.HTML("<p class='ink-sample-caption'>Sample: blue-ink cursive note about Andrej Karpathy and vibe-coding. Load it, then choose demo or live analysis.</p>")
                        gr.HTML(
                            f"""
                            <div class='ink-note'><strong>Best input:</strong> uncropped JPEG/PNG/WEBP, 1080p or higher. {SAFE_USE_NOTE}</div>
                            <div class='ink-boundary'><strong>Boundary:</strong> {DISCLAIMER}</div>
                            """
                        )

                    with gr.Column(scale=8, elem_classes=["ink-card", "ink-output-card", "ink-output"]):
                        gr.HTML(
                            """
                            <h2 class='ink-section-title'>Reading desk</h2>
                            <p class='ink-helper'>The report uses the wide panel: persona interpretation first, then alternatives, limitations, and structured JSON.</p>
                            """
                        )
                        with gr.Tabs():
                            with gr.Tab("Persona report"):
                                report = gr.Markdown(value=EMPTY_REPORT, label="Report")
                            with gr.Tab("Structured JSON"):
                                raw_json = gr.Textbox(value="{}", label="Structured JSON", lines=24, max_lines=24, interactive=False)
                        gr.HTML(
                            "<p class='ink-sample-caption'>If live output returns imperfect JSON, InkPersona normalizes common shorthand before rendering.</p>"
                        )

        sample.click(load_sample_image, outputs=[image, use_demo])
        analyze.click(analyze_for_gradio, inputs=[image, use_demo], outputs=[report, raw_json])
    return demo


demo = build_app()

if __name__ == "__main__":
    demo.launch()

