---
title: InkPersona
emoji: ✍️
colorFrom: purple
colorTo: yellow
sdk: gradio
sdk_version: 5.9.1
app_file: app.py
pinned: false
license: mit
---

# InkPersona

InkPersona is a Hugging Face Spaces / Gradio app for AI handwriting style analysis.

It accepts a full-HD scanned handwritten document, generates a persona-first graphology-inspired reading, and keeps scan observations, limitations, safety notes, and objective traits in a separate Detailed Analysis section.

Important: handwriting alone is not a validated way to determine personality. InkPersona must not be used for clinical, hiring, legal, school, employment, or other high-stakes decisions.

## Hugging Face Space setup

Create a Gradio Space, then push this repo with these root files:

- `app.py`
- `requirements.txt` — generated from `pyproject.toml` for Hugging Face compatibility
- `pyproject.toml`
- `uv.lock`
- `backend/`
- `datasets/`
- `README.md`

Add Space Secrets in Hugging Face:

- `OPENAI_API_KEY`: your OpenAI API key

Optional Space Variables:

- `OPENAI_MODEL`: default `gpt-4o-mini`
- `OPENAI_TEMPERATURE`: default `0.2`
- `OPENAI_MAX_OUTPUT_TOKENS`: default `3500`

After adding secrets, restart the Space.

## Local Gradio run

1. Copy env:

```bash
cp .env.example .env
```

2. Add your OpenAI key to `.env`:

```bash
OPENAI_API_KEY=your_key_here
```

3. Install and run with uv:

```bash
uv sync --group dev
uv run python app.py
```

Open the printed local Gradio URL.

You can also run without an API key by enabling “Use demo result instead of live OpenAI call.” The app includes a built-in sample image, `assets/sample-andrej-karpathy-handwriting.jpg`, so visitors can try the upload flow immediately.

To refresh Hugging Face's `requirements.txt` after changing `pyproject.toml`:

```bash
uv lock
uv export --no-dev --format requirements-txt --no-hashes --output-file requirements.txt
```

## Project structure

```text
app.py                    # Gradio Space entrypoint and custom UI
assets/                   # Built-in sample handwriting images
backend/app/analyzer.py   # OpenAI vision call + mock demo analysis
backend/app/config.py     # Runtime settings
backend/app/prompt.py     # Safety-bounded analysis prompt
backend/app/traits.py     # Objective trait schema and disclaimer
datasets/                 # Dataset notes/registry for evaluation planning
tests/                    # Gradio app tests
backend/tests/            # Shared backend module tests
```

This repo is Gradio-first. The earlier React/Vite frontend and FastAPI API prototype were removed to keep deployment simple and Python-only.

## Tests

Run all Python verification:

```bash
uv run pytest
```

Run only Gradio tests:

```bash
uv run pytest tests
```

Run only backend module tests:

```bash
uv run pytest backend/tests
```

## Safety policy

The system prompt requires:

- objective observations before interpretation
- confidence per trait
- explicit limitations
- no deterministic personality claims
- no protected/high-stakes claims
- no medical/clinical/hiring judgments

The app may say:

- “visible handwriting traits”
- “possible style impression”
- “low-confidence self-reflection”

The app must not say:

- “true personality detected”
- “diagnosis”
- “hire / do not hire”
- “mental illness detected”
- “intelligence measured”
- “criminality / honesty inferred”

## Dataset notes

IAM, CVL, RIMES, KHATT, and historical handwriting collections are useful for testing handwriting feature extraction. They are not personality ground truth.

Community graphology datasets should be treated as weak exploratory leads unless audited and paired with validated questionnaire labels.
