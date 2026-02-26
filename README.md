# MedTech Phase Viewer 🩻

A full-stack medical imaging mini web-app for simulated surgical planning. Upload a 2D medical image, select an imaging phase, and instantly view the original vs. processed image side by side.

> ⚠️ **Simulation only.** This application has no clinical purpose.

---

## 🔗 Live Demo

| Component | URL |
|-----------|-----|
| **Frontend** | *(GitHub Pages URL — update after deployment)* |
| **Backend API** | *(Hugging Face Spaces URL — update after deployment)* |

---

## ✨ Features

- **Drag-and-drop** image upload (JPG / PNG, ≤ 10 MB)
- **Arterial phase** — contrast enhancement (simulates arterial CT enhancement)
- **Venous phase** — Gaussian smoothing (simulates venous diffusion)
- **Side-by-side comparison** — original (A) vs. processed (B or C)
- All image processing runs **exclusively on the Python backend**

---

## 🏗️ Architecture

```
User Browser (GitHub Pages)
    │  upload image + phase selection
    ▼
Frontend (HTML / CSS / JS)
    │  POST /process — multipart/form-data
    ▼
Backend API (FastAPI + Pillow — Hugging Face Spaces)
    │  returns processed image as base64
    ▼
Frontend displays both images side by side
```

---

## 📁 Repository Structure

```
.
├── index.html          # Frontend entry point
├── style.css           # Dark medical theme styles
├── script.js           # Upload, API calls, image display logic
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
# Python (from project root)
python -m http.server 3000
```

Then update `BACKEND_URL` in `script.js` to `http://localhost:8000`.

### Testing the API

```bash
# Health check
curl http://localhost:8000/

# Arterial phase
curl -X POST http://localhost:8000/process \
  -F "file=@your_image.jpg" \
  -F "phase=arterial"

# Venous phase
curl -X POST http://localhost:8000/process \
  -F "file=@your_image.jpg" \
  -F "phase=venous"
```

---

## 🌐 Deployment

### Backend → Hugging Face Spaces

1. Create a new **Space** at [huggingface.co/spaces](https://huggingface.co/spaces)
2. Choose **Docker** or **FastAPI** SDK
3. Push the contents of the `backend/` folder to the Space repository
4. Copy the Space URL (e.g. `https://your-username-space-name.hf.space`)
5. Update `BACKEND_URL` in `script.js` with that URL

### Frontend → GitHub Pages

1. Push this repository to GitHub
2. Go to **Settings → Pages → Source: Deploy from branch → `main` / `(root)`**
3. GitHub will publish `index.html` at `https://your-username.github.io/your-repo/`

---

## 🧠 Image Processing Details

| Phase | Method | Library | Effect |
|-------|--------|---------|--------|
| Arterial | `ImageEnhance.Contrast` (×1.8) | Pillow | Increased contrast |
| Venous | `GaussianBlur` (radius=3) | Pillow | Smooth / softened |

---

## 📦 Backend Dependencies

| Package | Purpose |
|---------|---------|
| `fastapi` | Web framework |
| `uvicorn` | ASGI server |
| `python-multipart` | File upload parsing |
| `Pillow` | Image processing |
