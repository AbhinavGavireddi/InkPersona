# InkPersona

InkPersona is a Vite React + FastAPI MVP for AI handwriting style analysis.

It accepts full-HD scanned handwritten documents, extracts objective handwriting traits with an OpenAI vision model, and generates cautious reflection-oriented impressions.

Important: handwriting alone is not a validated way to determine personality. InkPersona must not be used for clinical, hiring, legal, or high-stakes decisions.

## Stack

- Frontend: Vite + React
- Backend: FastAPI
- Model API: OpenAI vision model
- Dataset strategy: IAM/CVL/RIMES/KHATT/Bentham-style handwriting datasets for objective feature evaluation; graphology/personality-labeled datasets only as weak exploratory leads unless validated.

## Setup

1. Copy env:

```bash
cp .env.example .env
```

2. Add your OpenAI key to `.env`:

```bash
OPENAI_API_KEY=your_key_here
```

3. Backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

4. Frontend:

```bash
cd frontend
npm install
npm run dev
```

Open: http://localhost:5173

## Environment variables

See `.env.example` for every required variable.

Key variables:

- `OPENAI_API_KEY`: OpenAI API key for live analysis.
- `OPENAI_MODEL`: default `gpt-4o-mini`.
- `INKPERSONA_MAX_UPLOAD_MB`: upload limit.
- `INKPERSONA_ALLOWED_ORIGINS`: CORS origins.
- `VITE_API_BASE_URL`: frontend API target.
- `VITE_ENABLE_MOCK_ANALYSIS`: enables demo result button.

## Objective trait groups

InkPersona covers:

- image quality
- layout
- size and proportion
- slant and baseline
- spacing
- stroke and pressure cues
- letter form
- consistency and legibility

Full registry lives in `backend/app/traits.py` and `datasets/dataset-registry.json`.

## API

- `GET /health`
- `GET /traits`
- `GET /mock-analysis`
- `POST /analyze` with multipart `file` JPEG/PNG/WEBP

## Tests

Backend:

```bash
cd backend
pytest
```

Frontend:

```bash
cd frontend
npm test
npm run build
```

## Safety policy

The system prompt requires:

- objective observations before interpretation
- confidence per trait
- explicit limitations
- no deterministic personality claims
- no protected/high-stakes claims
- no medical/clinical/hiring judgments
