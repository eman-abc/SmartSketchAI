# 🕵️ SmartSketch AI — Master Sprint Plan & Defence Checklist

**Role:** Staff Architect + Academic Reviewer  
**Date:** 2026-05-01  
**Goal:** Flawless Production Showcase + 5/5 FYDP-II Defence  

> Tasks are ordered sequentially for a 12-hour sprint. Each item is tagged by layer.
> - `[BACKEND]` — Django / LangGraph / API
> - `[ML]` — Modal, SDXL, GPU config, agent nodes
> - `[FRONTEND]` — React, TypeScript, UI/UX

---

## ✅ PHASE 1 — Critical Security & Stability (Hours 1–2)

### 1.1 `[BACKEND]` Fix Pickle RCE Vulnerability — `ml_engine/persistence.py`
- **Risk:** `pickle.dumps()` / `pickle.loads()` executes arbitrary code on deserialization. A manipulated `thread_id` state can compromise the server — catastrophic in a forensic application.
- **Fix:** Migrate `checkpoint_data` and `metadata_data` serialization to **JSON / Pydantic**.
- **Academic Link:** NFR-1 (Security) — "Zero code execution via state deserialization."
- **Checklist:** `pickle` fully replaced with `json` in `persistence.py` ✅

---

### 1.2 `[ML]` Prevent VRAM OOM Crash — `ml_service/modal_app.py`
- **Risk:** `gpu="T4"` (16GB) is too tight. SDXL FP16 (~8GB) + Qwen 2.5-3B (~6GB) + ControlNet/IP-Adapter/GFPGAN/CLIP (~3GB) = ~17GB total. A single inpaint or concurrent request triggers an **OOM crash**.
- **Fix (Option A — Recommended):** Upgrade to `gpu="L4"` (24GB).
- **Fix (Option B — Budget):** Add `torch.cuda.empty_cache()` between agent nodes.

---

### 1.3 `[FRONTEND]` Prevent "White Screen of Death" — `frontend/src/main.tsx`
- **Risk:** React 19 unmounts the entire component tree on any unhandled error (e.g., malformed `generateResult`).
- **Fix:** Wrap the app root in a `GlobalErrorBoundary` component — `ErrorBoundary.tsx` — with a professional "Forensic System Recovery" fallback UI.

---

## ✅ PHASE 2 — Agentic Resiliency (Hours 3–5)

### 2.1 `[BACKEND]` Self-Healing JSON Parser — `ml_engine/agent_nodes.py`
- **Risk:** `AnalyzerNode` uses a fragile `re.search` for JSON extraction. LLMs (including Gemini) occasionally output trailing commas or markdown fences that break `json.loads`.
- **Fix:** Implement a **Self-Healing Parser** — if parsing fails, retry the LLM call with the error message injected into the prompt.
- **Academic Link:** Demonstrates **Advanced AI Orchestration** and **Multi-Modal Feedback Loops**.

---

### 2.2 `[BACKEND]` Async Modal Calls — `ml_engine/agent_nodes.py`
- **Risk:** `AnalyzerNode` calls Modal via synchronous `requests.post`, blocking the Django worker thread for 30+ seconds.
- **Fix:** Convert `AnalyzerNode` to `async` and replace with `httpx.AsyncClient`.

---

### 2.3 `[BACKEND]` Add Prompt Injection Guardrails — `ml_engine/agent_nodes.py`
- **Fix:** Add detection logic for attempts to bypass forensic constraints in user prompts (e.g., jailbreak phrases, out-of-scope instructions).
- **Academic Link:** Security hardening; reinforces chain-of-custody integrity.

---

## ✅ PHASE 3 — Transparency Layer / SSE Streaming (Hours 6–9)

### 3.1 `[BACKEND]` Stream Agent Status via SSE — `api/views.py`
- **Problem:** Users see a static spinner for 30+ seconds with no feedback.
- **Fix:** Convert the forensic endpoint to `StreamingHttpResponse` using **Server-Sent Events (SSE)**.
- **Events to stream:**
  - `[Analyzer] Extracting eye color...`
  - `[Modal] Warming SDXL Engine...`
  - `[Artist] Denoising: 45%...`
- **HCI Rationale:** Nielsen's Heuristic #1 — Visibility of System Status.
- **Academic Link:** NFR-2 (Reliability) + UI/HCI rubric score lift (3/5 → 5/5).

---

### 3.2 `[FRONTEND]` Forensic Console UI — `frontend/src/components/ForensicConsole.tsx`
- **Fix:** Add a terminal-style real-time log component in the `RightPanel` that consumes the SSE stream from 3.1.
- **Visual Goal:** Live status log showing each LangGraph node's progress.

---

## ✅ PHASE 4 — Type Safety & Polish (Hours 10–12)

### 4.1 `[FRONTEND]` Strict TypeScript Interfaces — `frontend/src/types.ts`
- **Fix:** Replace all `any` types with strict, named interfaces for every Modal response shape.
- **Academic Link:** Code quality and PLO 4 (System Testing) rubric.

---

### 4.2 `[BACKEND]` Add SHA-256 Integrity Hash to Outputs
- **Fix:** Sign every generated output with a SHA-256 hash (visible in the `RightPanel` Metadata panel).
- **Academic Link:** NFR-3 (Forensic Integrity) — "Chain of custody integrity for every output."

---

## ✅ PHASE 5 — Performance Testing (PLO 4)

### 5.1 `[BACKEND]` Load Test Script — `backend-service/tests/performance_load_test.py`

```python
import time
import requests
import concurrent.futures

BASE_URL = "http://localhost:8000/api"

def simulate_investigator_request():
    start = time.time()
    resp = requests.post(f"{BASE_URL}/forensic/generate/", json={
        "prompt": "Test forensic sketch", "case_type": "criminal"
    })
    latency = time.time() - start
    return resp.status_code, latency

def run_load_test(users=5):
    print(f"🚀 Simulating {users} concurrent investigators...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=users) as executor:
        results = list(executor.map(lambda _: simulate_investigator_request(), range(users)))

    avg_latency = sum(r[1] for r in results) / users
    success_rate = (len([r for r in results if r[0] == 200]) / users) * 100
    print(f"📊 Results: Success Rate {success_rate}%, Avg Latency: {avg_latency:.2f}s")

if __name__ == "__main__":
    run_load_test(5)
```

- **Action:** Run this, screenshot results, and include in the "Experimental Results" chapter of the report.
- **Academic Link:** PLO 4 — Non-functional / performance testing evidence.

---

## 🌟 PHASE 6 — "WOW" Factor Features (Best Project Nomination)

### 6.1 `[BACKEND]` Forensic Dossier — Automated PDF Export
- **Feature:** A legal-ready PDF report auto-generated per session.
- **Contents:** Final sketch image, ArcFace identity scores, SHA-256 hash, turn-by-turn prompt audit trail.
- **Academic Link:** PLO 11 (Project Management) + PLO 12 (Life-long Learning). Demonstrates integration of legal/forensic standards.

---

### 6.2 `[ML]` Forensic Critic — AI Vision Self-Correction Loop
- **Feature:** A Gemini 1.5 Flash Vision loop that inspects the generated image and provides reasoning for further adjustments.
- **Tech Pattern:** SDXL generates → Gemini Vision analyzes → Agent verifies or re-generates.
- **Academic Link:** Advanced AI Orchestration, Multi-Modal Feedback Loops.
ADDED
---

### 6.3 `[FRONTEND]` Voice Investigator — Multimodal Input
- **Feature:** Hands-free forensic sketching via the browser's Web Speech API.
- **Tech Pattern:** Browser Speech API → Text → LangGraph Analyzer → Image Generation.
- **Academic Link:** HCI Excellence (hands-free interaction, accessibility).

---

## 🎤 Open House Demo Script

| Step | Action | What to Explain |
|------|--------|-----------------|
| **1 — Hook** | State the description: *"Male, late 40s, sharp nose, blue eyes."* | Sets the investigator scenario. |
| **2 — Logic** | Click Generate; while loading, narrate. | Explain the **LangGraph Analyzer Node** extracting facial features. |
| **3 — Surgical Edit** | Type: *"Witness says thick glasses."* | Show the **Inpaint Router** changing only the eye region. |
| **4 — Wow** | Move the Age Slider: *"What does he look like in 20 years?"* | Show **Identity-Consistent Aging**. |

**Pitch Line:**
> "SmartSketch AI solves the critical 4-week backlog in forensic sketching. We reduce sketch turnaround to 60 seconds while maintaining a 92% identity preservation score — with full chain-of-custody integrity via SHA-256 signing. Our B2G commercialization targets secure, air-gapped Cloud GPU deployments."

---

## 📋 SRS — Non-Functional Requirements to Add

| ID | Category | Requirement |
|----|----------|-------------|
| NFR-1 | Security | Zero code execution via state deserialization — JSON/Pydantic only, no Pickle. |
| NFR-2 | Reliability | 99.9% uptime via Tiered LLM Redundancy (Gemini → Modal Qwen fallback). |
| NFR-3 | Forensic Integrity | Every output signed with a SHA-256 hash for chain-of-custody compliance. |

---

## 🗂️ File Impact Summary

| File | Action | Tag | Priority |
|------|--------|-----|----------|
| `ml_engine/persistence.py` | Replace `pickle` with `json` | `[BACKEND]` | 🔴 Critical |
| `ml_service/modal_app.py` | Upgrade to `L4` GPU | `[ML]` | 🔴 Critical |
| `frontend/src/main.tsx` | Add `GlobalErrorBoundary` | `[FRONTEND]` | 🟡 High |
| `ml_engine/agent_nodes.py` | Self-healing parser + async calls + guardrails | `[BACKEND]` | 🟡 High |
| `api/views.py` | SSE `StreamingHttpResponse` | `[BACKEND]` | 🔵 High UX |
| `frontend/src/components/ForensicConsole.tsx` | Real-time SSE log terminal | `[FRONTEND]` | 🔵 High UX |
| `frontend/src/types.ts` | Strict TypeScript interfaces | `[FRONTEND]` | 🟢 Polish |
| `tests/performance_load_test.py` | Run & screenshot for PLO 4 | `[BACKEND]` | 🟢 Academic |

---

## ✅ Final Defence Checklist

- [m] `[BACKEND]` `pickle` fully replaced with `json` in `persistence.py`
- [x] `[ML]` GPU upgraded to `L4` or `empty_cache()` added between nodes
- [x] `[FRONTEND]` `GlobalErrorBoundary` wrapping app root
- [x] `[BACKEND]` Self-healing JSON parser live in `agent_nodes.py`
- [m] `[BACKEND]` Async `httpx` calls replacing blocking `requests.post`
- [ ] `[BACKEND]` SSE streaming endpoint in `views.py`
- [ ] `[FRONTEND]` Forensic Console real-time log in `RightPanel`
<!-- - [ ] `[BACKEND]` SHA-256 hashes visible in `RightPanel` Metadata -->
- [ ] `[BACKEND]` Performance load test run + results screenshot captured
- [ ] `[BACKEND]` GitHub Action CI shows green ✅
- [ ] `[BACKEND/ML]` Forensic Dossier PDF export functional (WOW)
