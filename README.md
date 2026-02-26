# MedTech Phase Viewer 🩻

A full-stack medical imaging mini web-app for simulated surgical planning. Upload a 2D medical image, select an imaging phase, and instantly view the original vs. processed image side by side. The `feature/organ-detection` branch also adds AI-powered liver region detection.

> ⚠️ **Simulation only.** This application has no clinical purpose.

---

## 🔗 Live Demos

| Branch | Frontend | Backend API |
|--------|----------|-------------|
| **`main`** | [baha2rm98.github.io/MedTech_WebApp/](https://baha2rm98.github.io/MedTech_WebApp/) | [baha2rm98-medtech-api.hf.space](https://baha2rm98-medtech-api.hf.space) |
| **`feature/organ-detection`** | *(deploy GitHub Pages from this branch)* | *(deploy new HF Space with this branch's backend)* |

---

## ✨ Features

### `main` branch
- **Drag-and-drop** image upload (JPG / PNG, ≤ 10 MB)
- **Arterial phase** — contrast enhancement (simulates arterial CT enhancement)
- **Venous phase** — Gaussian smoothing (simulates venous diffusion)
- **Side-by-side comparison** — original (A) vs. processed (B or C)

### `feature/organ-detection` branch (this branch)
- Everything above, **plus**:
- **Liver region detection** — POST `/analyze` endpoint using OpenCV contour analysis
- **Analyze button** — displays detection result (detected ✅/❌, confidence %, bounding box)

---

## 🏗️ Architecture

```
User Browser
    │  upload image + phase selection
    ▼
Frontend (HTML / CSS / JS)
    │  POST /process — multipart/form-data
    │  POST /analyze — multipart/form-data
    ▼
Backend API (FastAPI + Pillow + OpenCV — Hugging Face Spaces)
    │  /process → returns processed image as base64
    │  /analyze → returns liver detection result as JSON
    ▼
Frontend displays results
```

---

## 📁 Repository Structure

```
.
├── index.html          # Frontend entry point
├── style.css           # Dark medical theme styles
├── script.js           # Upload, API calls, image display + analyze logic
├── backend/
│   ├── app.py          # FastAPI application
│   └── requirements.txt
└── README.md
```

---

## 🚀 Local Development

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app:app --reload --port 8000
```

API will be available at `http://localhost:8000`.  
Interactive docs: `http://localhost:8000/docs`

### Frontend

Open `index.html` directly in a browser, **or** use a local HTTP server:

```bash
python -m http.server 3000
```

Then update `BACKEND_URL` in `script.js` to `http://localhost:8000`.

---

## 🧠 API Endpoints

### `POST /process` — Phase Image Processing

| Field | Type | Description |
|-------|------|-------------|
| `file` | UploadFile | JPG or PNG image |
| `phase` | string | `"arterial"` or `"venous"` |

**Response:**
```json
{ "processed_image": "data:image/png;base64,..." }
```

---

### `POST /analyze` — Liver Region Detection *(feature/organ-detection branch)*

| Field | Type | Description |
|-------|------|-------------|
| `file` | UploadFile | JPG or PNG image |

**Response:**
```json
{
  "detected": true,
  "confidence": 0.87,
  "bounding_box": { "x": 120, "y": 95, "width": 310, "height": 280 }
}
```

- `detected` — whether a liver-like region was found
- `confidence` — heuristic score 0.0–1.0 (based on contour area vs. expected liver size)
- `bounding_box` — pixel coordinates of the detected region, or `null` if not detected

**Detection method:** Otsu's adaptive thresholding → morphological closing → contour filtering by area, aspect ratio, and anatomical position (no deep learning required).

---

## 🌐 Deployment

### Backend → Hugging Face Spaces

1. Create a new **Space** at [huggingface.co/spaces](https://huggingface.co/spaces)
2. Push the contents of the `backend/` folder to the Space repository
3. Copy the Space URL and update `BACKEND_URL` in `script.js`

### Frontend → GitHub Pages

1. Go to **Settings → Pages → Source: Deploy from branch**
2. Select the branch (`main` or `feature/organ-detection`) and `/ (root)`

---

## 🧪 Image Processing Details

| Phase | Method | Library | Effect |
|-------|--------|---------|--------|
| Arterial | `ImageEnhance.Contrast` (×1.8) | Pillow | Increased contrast |
| Venous | `GaussianBlur` (radius=3) | Pillow | Smooth / softened |
| Analyze | Otsu threshold + contour heuristics | OpenCV | Liver region detection |

---

## 📦 Backend Dependencies

| Package | Purpose |
|---------|---------|
| `fastapi` | Web framework |
| `uvicorn` | ASGI server |
| `python-multipart` | File upload parsing |
| `Pillow` | Image processing |
| `opencv-python-headless` | Liver region detection (feature branch) |
