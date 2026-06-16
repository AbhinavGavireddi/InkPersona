from __future__ import annotations

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.analyzer import ALLOWED_IMAGE_TYPES, AnalysisError, analyze_handwriting_image, mock_analysis_result
from app.config import get_settings
from app.traits import DISCLAIMER, OBJECTIVE_TRAIT_GROUPS

settings = get_settings()

app = FastAPI(
    title="InkPersona API",
    version="0.1.0",
    description="Vision-LLM powered handwriting style analysis with cautious graphology-style framing.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "ok": True,
        "app": "InkPersona",
        "model": settings.openai_model,
        "max_upload_mb": settings.inkpersona_max_upload_mb,
    }


@app.get("/traits")
def traits() -> dict[str, object]:
    return {"groups": OBJECTIVE_TRAIT_GROUPS, "disclaimer": DISCLAIMER}


@app.get("/mock-analysis")
def mock_analysis() -> dict[str, object]:
    return mock_analysis_result().model_dump()


@app.post("/analyze")
async def analyze(file: UploadFile = File(...)) -> dict[str, object]:
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=415, detail="Upload JPEG, PNG, or WEBP scans only.")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Upload too large. Max {settings.inkpersona_max_upload_mb} MB.",
        )
    try:
        result = await analyze_handwriting_image(content, file.content_type, settings)
        return result.model_dump()
    except AnalysisError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
