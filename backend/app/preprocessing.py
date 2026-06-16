from __future__ import annotations

import io
from dataclasses import dataclass

import cv2
import numpy as np
from PIL import Image, ImageOps


TARGET_WIDTH = 1200
MIN_UPSCALE_WIDTH = 850
MAX_HEIGHT = 1800
WHITE_CROP_THRESHOLD = 245
CROP_PADDING_PX = 28
MIN_FOREGROUND_PIXELS = 50
MAX_DESKEW_DEGREES = 12.0


@dataclass(frozen=True)
class PreprocessedImage:
    content: bytes
    content_type: str
    summary: str
    metadata: dict[str, object]


def preprocess_handwriting_image(content: bytes) -> PreprocessedImage:
    """Prepare handwriting scans for vision-model analysis.

    Inspired by the Medium graphology pipeline the user shared:
    crop/normalize, bilateral denoising, grayscale + inverted binarization,
    dilation-assisted contour/affine deskewing, and horizontal/vertical
    projection features. We return a high-contrast PNG for the LLM plus compact
    metadata for the prompt.
    """

    original = _load_rgb_image(content)
    cropped, crop_box = _crop_to_handwriting(original)
    normalized = _normalize_size(cropped)

    rgb_array = np.array(normalized)
    denoised = cv2.bilateralFilter(rgb_array, d=7, sigmaColor=45, sigmaSpace=45)
    gray = cv2.cvtColor(denoised, cv2.COLOR_RGB2GRAY)
    gray = cv2.equalizeHist(gray)

    _, inverted_binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    deskewed_binary, skew_degrees = _deskew_binary(inverted_binary)
    cleaned_binary = _remove_tiny_noise(deskewed_binary)

    projection = _projection_metadata(cleaned_binary)
    output_image = Image.fromarray(255 - cleaned_binary).convert("RGB")
    buffer = io.BytesIO()
    output_image.save(buffer, format="PNG", optimize=True)

    metadata: dict[str, object] = {
        "original_size": original.size,
        "crop_box": crop_box,
        "processed_size": output_image.size,
        "target_width": TARGET_WIDTH,
        "denoise": "bilateral filter, edge-preserving",
        "threshold": "Otsu global threshold, inverted for foreground extraction",
        "deskew_degrees": round(float(skew_degrees), 2),
        **projection,
    }
    return PreprocessedImage(
        content=buffer.getvalue(),
        content_type="image/png",
        summary=_build_summary(metadata),
        metadata=metadata,
    )


def _load_rgb_image(content: bytes) -> Image.Image:
    with Image.open(io.BytesIO(content)) as image:
        return ImageOps.exif_transpose(image).convert("RGB")


def _crop_to_handwriting(image: Image.Image) -> tuple[Image.Image, tuple[int, int, int, int]]:
    grayscale = ImageOps.grayscale(image)
    arr = np.array(grayscale)
    foreground = arr < WHITE_CROP_THRESHOLD
    if int(foreground.sum()) < MIN_FOREGROUND_PIXELS:
        return image.copy(), (0, 0, image.width, image.height)

    ys, xs = np.where(foreground)
    left = max(int(xs.min()) - CROP_PADDING_PX, 0)
    top = max(int(ys.min()) - CROP_PADDING_PX, 0)
    right = min(int(xs.max()) + CROP_PADDING_PX + 1, image.width)
    bottom = min(int(ys.max()) + CROP_PADDING_PX + 1, image.height)
    box = (left, top, right, bottom)
    return image.crop(box), box


def _normalize_size(image: Image.Image) -> Image.Image:
    width, height = image.size
    target_width = width
    if width > TARGET_WIDTH:
        target_width = TARGET_WIDTH
    elif width < MIN_UPSCALE_WIDTH:
        target_width = MIN_UPSCALE_WIDTH

    if target_width != width:
        target_height = max(1, round(height * target_width / width))
        image = image.resize((target_width, target_height), Image.Resampling.LANCZOS)

    if image.height > MAX_HEIGHT:
        target_width = max(1, round(image.width * MAX_HEIGHT / image.height))
        image = image.resize((target_width, MAX_HEIGHT), Image.Resampling.LANCZOS)

    return image


def _deskew_binary(inverted_binary: np.ndarray) -> tuple[np.ndarray, float]:
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (100, 5))
    dilated = cv2.dilate(inverted_binary, kernel, iterations=1)
    coords = cv2.findNonZero(dilated)
    if coords is None or len(coords) < MIN_FOREGROUND_PIXELS:
        return inverted_binary, 0.0

    rect = cv2.minAreaRect(coords)
    angle = float(rect[-1])
    if angle < -45:
        angle = 90 + angle
    elif angle > 45:
        angle = angle - 90

    if abs(angle) < 0.25 or abs(angle) > MAX_DESKEW_DEGREES:
        return inverted_binary, 0.0

    height, width = inverted_binary.shape[:2]
    matrix = cv2.getRotationMatrix2D((width / 2, height / 2), angle, 1.0)
    rotated = cv2.warpAffine(
        inverted_binary,
        matrix,
        (width, height),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0,
    )
    return rotated, angle


def _remove_tiny_noise(inverted_binary: np.ndarray) -> np.ndarray:
    kernel = np.ones((2, 2), np.uint8)
    opened = cv2.morphologyEx(inverted_binary, cv2.MORPH_OPEN, kernel, iterations=1)
    return cv2.morphologyEx(opened, cv2.MORPH_CLOSE, kernel, iterations=1)


def _projection_metadata(inverted_binary: np.ndarray) -> dict[str, object]:
    foreground = inverted_binary > 0
    ink_pixels = int(foreground.sum())
    total_pixels = int(foreground.size)
    row_projection = foreground.sum(axis=1)
    col_projection = foreground.sum(axis=0)
    line_band_count = _count_projection_bands(row_projection, threshold=max(2, inverted_binary.shape[1] * 0.012))
    column_band_count = _count_projection_bands(col_projection, threshold=max(2, inverted_binary.shape[0] * 0.008))

    rows = np.where(row_projection > 0)[0]
    cols = np.where(col_projection > 0)[0]
    if len(rows) and len(cols):
        top_margin_ratio = float(rows.min() / inverted_binary.shape[0])
        left_margin_ratio = float(cols.min() / inverted_binary.shape[1])
        text_area_ratio = float(((rows.max() - rows.min() + 1) * (cols.max() - cols.min() + 1)) / total_pixels)
    else:
        top_margin_ratio = 0.0
        left_margin_ratio = 0.0
        text_area_ratio = 0.0

    return {
        "ink_density_percent": round(ink_pixels / total_pixels * 100, 2) if total_pixels else 0.0,
        "estimated_line_bands": line_band_count,
        "estimated_vertical_bands": column_band_count,
        "top_margin_ratio": round(top_margin_ratio, 3),
        "left_margin_ratio": round(left_margin_ratio, 3),
        "text_area_ratio": round(text_area_ratio, 3),
    }


def _count_projection_bands(projection: np.ndarray, threshold: float) -> int:
    active = projection > threshold
    if not bool(active.any()):
        return 0
    starts = np.logical_and(active, np.concatenate(([True], ~active[:-1])))
    return int(starts.sum())


def _build_summary(metadata: dict[str, object]) -> str:
    return (
        "Preprocessed before vision-model analysis using crop/width normalization, "
        "bilateral denoising, grayscale contrast normalization, inverted Otsu binarization, "
        "dilation-assisted contour deskew, and projection metadata. "
        f"Processed size: {metadata['processed_size']}; deskew: {metadata['deskew_degrees']}°; "
        f"ink density: {metadata['ink_density_percent']}%; estimated text lines: {metadata['estimated_line_bands']}."
    )
