/**
 * MedTech Phase Viewer — Frontend Script
 * ----------------------------------------
 * Handles:
 *  1. Drag-and-drop + click-to-browse image upload
 *  2. Phase selection (arterial / venous)
 *  3. Sending image + phase to the backend API
 *  4. Displaying original and processed images side by side
 *
 * NOTE: Update BACKEND_URL below after deploying to Hugging Face Spaces.
 */

// ─── Configuration ────────────────────────────────────────────────────────────
// Replace this with your actual Hugging Face Spaces URL after deployment.
// Example: "https://your-username-medtech-api.hf.space"
const BACKEND_URL = "https://baha2rm98-medtech-api.hf.space";

// ─── DOM References ───────────────────────────────────────────────────────────
const dropZone = document.getElementById("drop-zone");
const dropContent = document.getElementById("drop-zone-content");
const fileInput = document.getElementById("file-input");
const processBtn = document.getElementById("process-btn");
const errorMsg = document.getElementById("error-msg");
const resultsSection = document.getElementById("results-section");
const originalImg = document.getElementById("original-img");
const processedImg = document.getElementById("processed-img");
const processedBadge = document.getElementById("processed-badge");
const processedLabel = document.getElementById("processed-label");
const resultsDesc = document.getElementById("results-desc");

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

    updateProcessButton();
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

// Update the process button whenever a phase radio is changed
document.querySelectorAll('input[name="phase"]').forEach((radio) => {
    radio.addEventListener("change", () => {
        clearError();
        updateProcessButton();
    });
});

/** Returns the currently selected phase ("arterial" | "venous" | null) */
function getSelectedPhase() {
    const checked = document.querySelector('input[name="phase"]:checked');
    return checked ? checked.value : null;
}

// ─── Button State ─────────────────────────────────────────────────────────────

/** Enables the Process button only when both a file and a phase are selected */
function updateProcessButton() {
    processBtn.disabled = !(uploadedFile && getSelectedPhase());
}

// ─── Form Submission → API Call ───────────────────────────────────────────────

processBtn.addEventListener("click", async () => {
    const phase = getSelectedPhase();
    if (!uploadedFile || !phase) return;

    // Show loading state
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

        // ── Display results ──
        // Original image (read from the uploaded file)
        const originalURL = URL.createObjectURL(uploadedFile);
        originalImg.src = originalURL;

        // Processed image (base64 from backend)
        processedImg.src = data.processed_image;

        // Update panel labels based on phase
        if (phase === "arterial") {
            processedBadge.textContent = "B";
            processedLabel.textContent = "Arterial Phase";
            resultsDesc.textContent = "Contrast-enhanced image (arterial phase simulation)";
        } else {
            processedBadge.textContent = "C";
            processedLabel.textContent = "Venous Phase";
            resultsDesc.textContent = "Gaussian-smoothed image (venous phase simulation)";
        }

        // Show the results section with animation
        resultsSection.hidden = false;
        resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });

    } catch (err) {
        showError(`Processing failed: ${err.message}`);
    } finally {
        // Restore button
        processBtn.classList.remove("loading");
        updateProcessButton();
    }
});

// ─── Error Utilities ──────────────────────────────────────────────────────────

function showError(msg) {
    errorMsg.textContent = msg;
}

function clearError() {
    errorMsg.textContent = "";
}
