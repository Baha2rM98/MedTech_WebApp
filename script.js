/**
 * MedTech Phase Viewer — Frontend Script
 * ----------------------------------------
 * Handles:
 *  1. Drag-and-drop + click-to-browse image upload
 *  2. Phase selection (arterial / venous)
 *  3. Sending image + phase to the backend /process API
 *  4. Sending image to the backend /analyze API for liver detection
 *  5. Displaying original and processed images side by side
 *
 * NOTE: Update BACKEND_URL below after deploying to Hugging Face Spaces.
 * For the feature/organ-detection branch, use the NEW HF Space URL.
 */

// ─── Configuration ────────────────────────────────────────────────────────────
const BACKEND_URL = "https://baha2rm98-feature-organ-detection.hf.space";

// ─── DOM References ───────────────────────────────────────────────────────────
const dropZone = document.getElementById("drop-zone");
const dropContent = document.getElementById("drop-zone-content");
const fileInput = document.getElementById("file-input");
const processBtn = document.getElementById("process-btn");
const analyzeBtn = document.getElementById("analyze-btn");
const errorMsg = document.getElementById("error-msg");
const analyzeErrorMsg = document.getElementById("analyze-error-msg");
const resultsSection = document.getElementById("results-section");
const originalImg = document.getElementById("original-img");
const processedImg = document.getElementById("processed-img");
const processedBadge = document.getElementById("processed-badge");
const processedLabel = document.getElementById("processed-label");
const resultsDesc = document.getElementById("results-desc");

// Analyze result elements
const analyzeResult = document.getElementById("analyze-result");
const analyzeDetected = document.getElementById("analyze-detected");
const analyzeConfidence = document.getElementById("analyze-confidence");
const analyzeBboxSection = document.getElementById("analyze-bbox-section");
const analyzeBbox = document.getElementById("analyze-bbox");

// ─── State ────────────────────────────────────────────────────────────────────
let uploadedFile = null;

// ─── Upload Handling ──────────────────────────────────────────────────────────

/**
 * Called after a valid file is chosen. Stores the file, shows a preview,
 * and updates the UI state of the drop zone.
 */
function handleFile(file) {
    if (!file) return;

    const allowed = ["image/jpeg", "image/png"];
    if (!allowed.includes(file.type)) {
        showError("Please upload a JPG or PNG image.");
        return;
    }
    if (file.size > 10 * 1024 * 1024) {
        showError("File is too large. Maximum size is 10 MB.");
        return;
    }

    uploadedFile = file;
    clearError();
    clearAnalyzeError();
    analyzeResult.hidden = true; // Reset previous analyze result on new file

    // Show preview inside the drop zone
    const reader = new FileReader();
    reader.onload = (e) => {
        // Remove old preview if any
        const old = dropZone.querySelector(".drop-preview");
        if (old) old.remove();

        const preview = document.createElement("img");
        preview.src = e.target.result;
        preview.alt = "Uploaded image preview";
        preview.className = "drop-preview";
        dropZone.appendChild(preview);
        dropZone.classList.add("has-image");
    };
    reader.readAsDataURL(file);

    updateButtons();
}

// Drag-and-drop events
dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("dragover");
});

dropZone.addEventListener("dragleave", () => {
    dropZone.classList.remove("dragover");
});

dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("dragover");
    const file = e.dataTransfer.files[0];
    handleFile(file);
});

// Click-to-browse via the hidden file input
fileInput.addEventListener("change", () => {
    handleFile(fileInput.files[0]);
});

// Keyboard accessibility for the drop zone
dropZone.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        fileInput.click();
    }
});

// ─── Phase Selection ──────────────────────────────────────────────────────────

document.querySelectorAll('input[name="phase"]').forEach((radio) => {
    radio.addEventListener("change", () => {
        clearError();
        updateButtons();
    });
});

/** Returns the currently selected phase ("arterial" | "venous" | null) */
function getSelectedPhase() {
    const checked = document.querySelector('input[name="phase"]:checked');
    return checked ? checked.value : null;
}

// ─── Button State ─────────────────────────────────────────────────────────────

/** Enables Process button when both file and phase are selected; Analyze when file is selected */
function updateButtons() {
    processBtn.disabled = !(uploadedFile && getSelectedPhase());
    analyzeBtn.disabled = !uploadedFile;
}

// ─── /process API Call ────────────────────────────────────────────────────────

processBtn.addEventListener("click", async () => {
    const phase = getSelectedPhase();
    if (!uploadedFile || !phase) return;

    processBtn.classList.add("loading");
    processBtn.disabled = true;
    clearError();
    resultsSection.hidden = true;

    try {
        const formData = new FormData();
        formData.append("file", uploadedFile);
        formData.append("phase", phase);

        const response = await fetch(`${BACKEND_URL}/process`, {
            method: "POST",
            body: formData,
        });

        if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            throw new Error(errData.detail || `Server returned ${response.status}`);
        }

        const data = await response.json();
        if (!data.processed_image) {
            throw new Error("No processed image received from server.");
        }

        // Display results
        originalImg.src = URL.createObjectURL(uploadedFile);
        processedImg.src = data.processed_image;

        if (phase === "arterial") {
            processedBadge.textContent = "B";
            processedLabel.textContent = "Arterial Phase";
            resultsDesc.textContent = "Contrast-enhanced image (arterial phase simulation)";
        } else {
            processedBadge.textContent = "C";
            processedLabel.textContent = "Venous Phase";
            resultsDesc.textContent = "Gaussian-smoothed image (venous phase simulation)";
        }

        resultsSection.hidden = false;
        resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });

    } catch (err) {
        showError(`Processing failed: ${err.message}`);
    } finally {
        processBtn.classList.remove("loading");
        updateButtons();
    }
});

// ─── /analyze API Call ────────────────────────────────────────────────────────

analyzeBtn.addEventListener("click", async () => {
    if (!uploadedFile) return;

    analyzeBtn.classList.add("loading");
    analyzeBtn.disabled = true;
    clearAnalyzeError();
    analyzeResult.hidden = true;

    try {
        const formData = new FormData();
        formData.append("file", uploadedFile);

        const response = await fetch(`${BACKEND_URL}/analyze`, {
            method: "POST",
            body: formData,
        });

        if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            throw new Error(errData.detail || `Server returned ${response.status}`);
        }

        const data = await response.json();

        // Display detection result
        analyzeDetected.textContent = data.detected ? "✅ Yes" : "❌ No";
        analyzeDetected.style.color = data.detected
            ? "var(--accent-teal, #4ecdc4)"
            : "var(--error, #e74c3c)";
        analyzeConfidence.textContent = `${(data.confidence * 100).toFixed(0)}%`;

        if (data.bounding_box) {
            const bb = data.bounding_box;
            analyzeBbox.textContent =
                `x: ${bb.x}px\ny: ${bb.y}px\nwidth:  ${bb.width}px\nheight: ${bb.height}px`;
            analyzeBboxSection.hidden = false;
        } else {
            analyzeBboxSection.hidden = true;
        }

        analyzeResult.hidden = false;
        analyzeResult.scrollIntoView({ behavior: "smooth", block: "nearest" });

    } catch (err) {
        showAnalyzeError(`Analysis failed: ${err.message}`);
    } finally {
        analyzeBtn.classList.remove("loading");
        updateButtons();
    }
});

// ─── Error Utilities ──────────────────────────────────────────────────────────

function showError(msg) { errorMsg.textContent = msg; }
function clearError() { errorMsg.textContent = ""; }
function showAnalyzeError(msg) { analyzeErrorMsg.textContent = msg; }
function clearAnalyzeError() { analyzeErrorMsg.textContent = ""; }
