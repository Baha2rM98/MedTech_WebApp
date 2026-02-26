"""
MedTech Image Processing Backend
---------------------------------
FastAPI backend for simulated surgical planning image processing.
Supports two imaging phases:
  - Arterial: contrast enhancement (simulates arterial phase imaging)
  - Venous: Gaussian smoothing (simulates venous phase imaging)

Deployed on Hugging Face Spaces.
"""

import io
import base64

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
    version="0.0.1",
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
ARTERIAL_CONTRAST_FACTOR = 1.8  # How much to boost contrast for the arterial phase
VENOUS_BLUR_RADIUS = 3  # Gaussian blur radius (pixels) for venous phase
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB upload limit
ALLOWED_FORMATS = {"JPEG", "PNG", "BMP", "WEBP"}


# ---------------------------------------------------------------------------
# Helper Functions
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
    # Convert to RGB to ensure consistent color processing
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
