"""
MedTech Image Processing Backend
---------------------------------
FastAPI backend for simulated surgical planning image processing.
Supports two imaging phases:
  - Arterial: contrast enhancement (simulates arterial phase imaging)
  - Venous: Gaussian smoothing (simulates venous phase imaging)

Also supports organ detection:
  - POST /analyze: detects whether the image contains a liver region using
    OpenCV-based thresholding and contour heuristics (no deep learning).

Deployed on Hugging Face Spaces.
"""

import io
import base64

import cv2
import numpy as np
from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from PIL import Image, ImageEnhance, ImageFilter

# ---------------------------------------------------------------------------
# App Setup
# ---------------------------------------------------------------------------
app = FastAPI(
    title="MedTech Image Processing API",
    description="Simulated medical image processing backend for surgical planning.",
    version="0.1.0",
)

# Allow cross-origin requests from the frontend (GitHub Pages or any origin).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
ARTERIAL_CONTRAST_FACTOR = 1.8   # Contrast boost factor for arterial phase
VENOUS_BLUR_RADIUS = 3           # Gaussian blur radius (pixels) for venous phase
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB upload limit
ALLOWED_FORMATS = {"JPEG", "PNG", "BMP", "WEBP"}

# Liver detection heuristics
# The liver typically occupies ~20-30% of the abdominal slice area.
# We use 25% as the "target" area for confidence normalisation.
LIVER_TARGET_AREA_RATIO = 0.25
LIVER_MIN_AREA_RATIO    = 0.02   # Contours smaller than 2% of image are noise
LIVER_ASPECT_MIN        = 0.4    # Liver bounding box aspect ratio lower bound
LIVER_ASPECT_MAX        = 2.5    # Liver bounding box aspect ratio upper bound
# In abdominal CT the liver sits in the right side, roughly centre-height.
# We constrain the centroid to the right 55% of width and middle 70% of height.
LIVER_X_MIN_RATIO       = 0.10
LIVER_X_MAX_RATIO       = 0.90
LIVER_Y_MIN_RATIO       = 0.15
LIVER_Y_MAX_RATIO       = 0.85


# ---------------------------------------------------------------------------
# Helper: Phase Processing (unchanged from original)
# ---------------------------------------------------------------------------

def encode_image_to_base64(image: Image.Image, fmt: str = "PNG") -> str:
    """Convert a PIL image to a base64-encoded data URI string."""
    buffer = io.BytesIO()
    image.save(buffer, format=fmt)
    buffer.seek(0)
    encoded = base64.b64encode(buffer.read()).decode("utf-8")
    mime = "image/png" if fmt == "PNG" else "image/jpeg"
    return f"data:{mime};base64,{encoded}"


def apply_arterial_phase(image: Image.Image) -> Image.Image:
    """
    Arterial Phase Simulation:
    Enhances image contrast to simulate the arterial enhancement pattern
    seen in contrast-enhanced CT imaging during the arterial phase.
    """
    image = image.convert("RGB")
    enhancer = ImageEnhance.Contrast(image)
    return enhancer.enhance(ARTERIAL_CONTRAST_FACTOR)


def apply_venous_phase(image: Image.Image) -> Image.Image:
    """
    Venous Phase Simulation:
    Applies Gaussian smoothing to simulate the softer, diffuse enhancement
    pattern seen in contrast-enhanced imaging during the venous phase.
    """
    image = image.convert("RGB")
    return image.filter(ImageFilter.GaussianBlur(radius=VENOUS_BLUR_RADIUS))


# ---------------------------------------------------------------------------
# Helper: Liver Region Detection (OpenCV-based, no deep learning)
# ---------------------------------------------------------------------------

def detect_liver_region(image_bytes: bytes) -> dict:
    """
    Detect whether the image contains a liver-like region using OpenCV.

    Algorithm:
      1. Decode image to grayscale via OpenCV.
      2. Apply Otsu's global thresholding — adaptive, no hardcoded threshold.
      3. Morphological closing (dilate then erode) to fill holes and remove
         small noise blobs produced by thresholding.
      4. Find external contours and filter candidates by:
           • Minimum area  : > LIVER_MIN_AREA_RATIO  of total image area
           • Aspect ratio  : between LIVER_ASPECT_MIN and LIVER_ASPECT_MAX
             (liver is a broad, roughly oval organ)
           • Centroid pos. : within the expected abdominal position bounds
             (right-center region in standard axial CT orientation)
      5. The largest surviving candidate is taken as the liver region.
      6. Confidence = contour_area / (LIVER_TARGET_AREA_RATIO * image_area),
         clamped to [0.0, 1.0]. This reflects how well the detected blob
         matches the expected liver size.

    Returns a dict:
      {
        "detected":     bool,
        "confidence":   float,         # 0.0 – 1.0
        "bounding_box": dict | None    # {x, y, width, height} in pixels
      }
    """
    # --- Decode to numpy grayscale array ---
    nparr = np.frombuffer(image_bytes, np.uint8)
    img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img_bgr is None:
        return {"detected": False, "confidence": 0.0, "bounding_box": None}

    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    img_h, img_w = gray.shape
    img_area = img_h * img_w

    # --- Otsu's thresholding (finds optimal threshold automatically) ---
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # --- Morphological closing: fill internal holes, smooth contour edges ---
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
    closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=2)

    # --- Find external contours ---
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # --- Filter contours with liver-specific heuristics ---
    candidates = []
    min_area = LIVER_MIN_AREA_RATIO * img_area

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area:
            continue  # Too small → noise

        x, y, w, h = cv2.boundingRect(cnt)
        aspect = w / h if h > 0 else 0
        if not (LIVER_ASPECT_MIN <= aspect <= LIVER_ASPECT_MAX):
            continue  # Wrong shape → not liver-like

        # Centroid of the contour
        M = cv2.moments(cnt)
        if M["m00"] == 0:
            continue
        cx = M["m10"] / M["m00"]
        cy = M["m01"] / M["m00"]

        # Check centroid is within expected abdominal position
        if not (LIVER_X_MIN_RATIO * img_w <= cx <= LIVER_X_MAX_RATIO * img_w):
            continue
        if not (LIVER_Y_MIN_RATIO * img_h <= cy <= LIVER_Y_MAX_RATIO * img_h):
            continue

        candidates.append((area, x, y, w, h))

    if not candidates:
        return {"detected": False, "confidence": 0.0, "bounding_box": None}

    # Take the largest surviving candidate
    candidates.sort(key=lambda c: c[0], reverse=True)
    best_area, x, y, w, h = candidates[0]

    # Confidence: how close is this blob to the expected liver area?
    target_area = LIVER_TARGET_AREA_RATIO * img_area
    confidence = round(min(best_area / target_area, 1.0), 2)

    return {
        "detected": True,
        "confidence": confidence,
        "bounding_box": {"x": int(x), "y": int(y), "width": int(w), "height": int(h)},
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", summary="Health Check")
def root():
    """Health check endpoint to verify the backend is running."""
    return {"status": "ok", "message": "MedTech Image Processing API is running."}


@app.post("/process", summary="Process Medical Image")
async def process_image(
        file: UploadFile = File(..., description="Medical image file (JPG or PNG)"),
        phase: str = Form(..., description="Imaging phase: 'arterial' or 'venous'"),
):
    """
    Process a medical image according to the selected imaging phase.

    - **arterial**: Increases contrast to simulate arterial enhancement
    - **venous**: Applies Gaussian smoothing to simulate venous diffusion

    Returns a JSON object with the processed image encoded as a base64 data URI.
    """
    # --- Validate phase ---
    phase = phase.strip().lower()
    if phase not in ("arterial", "venous"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid phase '{phase}'. Must be 'arterial' or 'venous'.",
        )

    # --- Validate file ---
    contents = await file.read()
    if len(contents) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Max size is 10 MB.")

    try:
        image = Image.open(io.BytesIO(contents))
    except Exception:
        raise HTTPException(status_code=400, detail="Could not decode image. Ensure it is a valid JPG or PNG.")

    if image.format not in ALLOWED_FORMATS and image.format is not None:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported image format '{image.format}'. Use JPG or PNG.",
        )

    # --- Apply processing ---
    if phase == "arterial":
        processed = apply_arterial_phase(image)
    else:
        processed = apply_venous_phase(image)

    # --- Encode and return ---
    processed_b64 = encode_image_to_base64(processed, fmt="PNG")
    return JSONResponse(content={"processed_image": processed_b64})


@app.post("/analyze", summary="Detect Liver Region")
async def analyze_image(
        file: UploadFile = File(..., description="Medical image file (JPG or PNG)"),
):
    """
    Detect whether the uploaded image contains a liver region.

    Uses OpenCV-based Otsu thresholding and contour heuristics — no deep learning.

    Returns:
    - **detected**: whether a liver-like region was found
    - **confidence**: heuristic score 0.0–1.0 based on blob area vs. expected liver size
    - **bounding_box**: pixel coordinates `{x, y, width, height}` of the detected region,
      or `null` if nothing was detected
    """
    # --- Validate file size ---
    contents = await file.read()
    if len(contents) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Max size is 10 MB.")

    # --- Run detection ---
    result = detect_liver_region(contents)
    return JSONResponse(content=result)
