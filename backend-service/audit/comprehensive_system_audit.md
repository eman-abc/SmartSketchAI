# SmartSketch AI: Comprehensive System Audit & Improvements
**Date:** 2026-05-01
**Status:** Post-Aging-Integration Review

## 🏗️ 1. Architectural Improvements

### A. Secure Serialization (Critical)
*   **Current Issue:** `DjangoCheckpointer` uses `pickle`, which is vulnerable to Remote Code Execution (RCE).
*   **Improvement:** Migrate state storage to **JSON** or **CBOR**. This requires updating `ForensicAgentState` to be fully JSON-serializable (converting PIL images to Base64 *before* they hit the checkpointer).
*   **Priority:** 🔴 High

### B. Scalable Model Management
*   **Current Issue:** Models are loaded into memory on demand or kept warm via crons.
*   **Improvement:** Implement a **Model Pool**. Instead of one monolithic pipeline, use a pool of specialized workers (Generator Worker, Inpaint Worker, Restorer Worker) to maximize GPU utilization and reduce context switching overhead.
*   **Priority:** 🟡 Medium

---

## 🧠 2. ML & Forensic Quality Improvements

### A. Vision-LLM Verification Loop ("The Critic")
*   **Current Issue:** The agent is "blind." It assumes the generation was successful based on a numeric CLIP score.
*   **Improvement:** Integrate a **Vision LLM (Gemini 1.5 Pro/Flash)** to inspect the output.
    *   *Workflow:* SDXL Generates → Gemini Vision analyzes image → Gemini compares image to Suspect Profile → "The nose is still too small, regenerating..."
*   **Priority:** 🔴 High (Game changer for forensic accuracy)

### B. Demographic Bias Mitigation
*   **Current Issue:** SDXL has a "beauty bias," often generating overly symmetrical or "model-like" faces which are counter-productive for suspect identification.
*   **Improvement:** Implement **Asymmetry Injection**. Update the `AnalyzerNode` to explicitly add keywords for realism (e.g., "facial asymmetry," "imperfect skin," "distinguishing moles," "natural pores") to every enhanced prompt.
*   **Priority:** 🟡 Medium

### C. Robust Face Detection
*   **Current Issue:** MTCNN (used for identity scoring) often fails on stylized sketches or side profiles.
*   **Improvement:** Switch to **InsightFace (SCRFD)** or **MediaPipe**. These models are more resilient to the "Sketch Gap" and extreme forensic angles.
*   **Priority:** 🟢 Low

---

## 🛡️ 3. Forensic Integrity & Legal Readiness

### A. Audit Trail & Metadata Embedding
*   **Current Issue:** Generation history is stored in DB, but the image file itself is "dumb."
*   **Improvement:** Inject **EXIF Metadata** into every PNG. Store the `generation_id`, `seed`, `prompt`, and `case_id` directly inside the image header.
*   **Priority:** 🟡 Medium

### B. Chain of Custody Logging
*   **Current Issue:** We track the current profile, but not the *deltas* (exactly what changed at each turn).
*   **Improvement:** Implement a **Profile Diff Log**. For every turn, store exactly which field was updated (e.g., `Field: eye_color, Old: brown, New: blue`). This is critical for legal testimony.
*   **Priority:** 🔴 High

---

## ⚡ 4. Performance & DX

### A. Modal Image Optimization
*   **Current Issue:** Every `modal deploy` runs a long list of `pip installs`.
*   **Improvement:** Create a **Base Docker Image** with `torch`, `diffusers`, and `mediapipe` pre-installed. This will reduce deployment times from minutes to seconds.
*   **Priority:** 🟡 Medium

### B. Unified Event Stream
*   **Current Issue:** The frontend polls for status or waits for long requests.
*   **Improvement:** Implement **Server-Sent Events (SSE)** or **WebSockets** to stream generation progress (e.g., "Step 1/30: Denoising...") back to the investigator in real-time.
*   **Priority:** 🟢 Low

---

## 📊 Improvement Priority Matrix

| Feature | Effort | Impact | Status |
|---|---|---|---|
| **Vision-LLM Critic** | Medium | 🔴 Critical | Proposed |
| **JSON Serialization**| Low | 🔴 Critical (Security) | Proposed |
| **EXIF Metadata** | Low | 🟡 High (Legal) | Proposed |
| **Demographic Bias** | Low | 🟡 High (Accuracy) | Proposed |
| **Model Pool** | High | 🟢 Medium (Performance)| Proposed |
| **SSE Progress** | Medium | 🟢 Medium (UX) | Proposed |
