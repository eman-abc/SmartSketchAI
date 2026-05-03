# Final defense — AI/ML supplement for SmartSketch.AI

Use this document to **expand slides 19–22**, fill **empty slides 19–20**, and align the deck with the **actual codebase**. Copy each block into a new PowerPoint slide (title + bullets as written).

---

## Gaps in the current PDF (vs repository)

| Topic in deck | Issue |
|---------------|--------|
| **Slides 19–20** | Blank in the export; ML narrative jumps straight to five components. |
| **Orchestration** | No slide on **LangGraph** (`analyze → route → artist → verify`, retry to `artist`). |
| **Structured memory** | No slide on **SuspectProfile** (Pydantic) and **ForensicAgentState** (thread state). |
| **Vision critic** | Not described: **Qwen2.5-VL** (default) on Modal, JSON report, `accept` / `revise`, prompt adjustment. |
| **Verification policy** | **CLIP + optional ArcFace** combined score (60/40 when identity present); threshold **50**; critic-driven retry; `MAX_RETRIES` / `critic_max_retries`. |
| **Deployment** | Slide 44 lists **Colab $10/mo** for AI/ML; production path in code is **Modal** (GPU class, persistent `Volume` for HF cache, FastAPI ASGI). Mention Colab only if you still use it for **experiments**. |
| **Analyzer** | Three-tier analysis: primary LLM → **Modal `/analyze`** (Qwen JSON + self-healing parse) → **heuristic fallback**. |
| **Integrity** | **SHA-256 forensic hash** + **invisible DWT-DCT watermark** (`ForensicSigner`); optional **SD safety checker** (`ForensicSafetyChecker`). |
| **Inpainting vs edit** | Router: **region keywords** → inpaint; else **ControlNet img2img**; Modal `/edit` also keyword-splits inpaint vs ControlNet. |
| **Typos (fix in master deck)** | Djando → Django; formsic → forensic; vedio → video; Deploymnet → Deployment. |

---

## Novel contributions (defense “what is new?”)

Say these as **your contributions**, grounded in implementation:

1. **Conversational forensic orchestration (LangGraph)** — Not a single “text-to-image” call: a **compiled state graph** with checkpointing, per-turn **analyze → route → artist → verify**, and **conditional retry** back to the artist.
2. **Structured witness memory** — **`SuspectProfile`** accumulates attributes across turns; **`to_detailed_prompt()`** turns structured fields into SDXL-ready text; **negative prompt sanitization** avoids negating desired traits already in the profile.
3. **Semantic tool routing** — **`RouterNode`** chooses **generate / edit / inpaint / age** from message text, **user_intent**, **age_params**, and **regenerate triggers** (“wrong person”, “start over”, …).
4. **Closed-loop quality** — **`VerificationNode`**: CLIP (+ ArcFace when available) **combined score**; optional **self-hosted VLM critic** with bounded **revise** loop and **`prompt_adjustment`** fed back into the next artist pass.
5. **Forensic delivery stack** — **Invisible watermark + content hash** on outputs; **JWT + audit / forensic request** flows on the app side (tie to SDG / ethics slide).
6. **Serverless GPU inference** — **Modal** `@app.cls` loads **`SmartSketchPipeline.from_pretrained`** once per container; HTTP **`/generate`**, **`/edit`**, **`/age`**, **`/analyze`**, **`/critic`**; **model weights on Modal Volume** to reduce cold-start.

---

## Suggested new slides (paste into PowerPoint)

### Slide A — “End-to-end AI/ML architecture”

**Title:** SmartSketch AI/ML — system view

**Bullets:**

- **Client:** React chat + forensic API calls to **Django REST**.
- **Orchestration:** **LangGraph** agent on Django — one graph invocation per user message (`SmartSketchAgent.run` → `app.invoke`).
- **Compute:** Heavy stack on **Modal** (GPU): same **`ml_engine`** package mounted in the container image; Django holds **no torch weights** in production (`USE_LOCAL_ML=False`).
- **Persistence:** **`AgentCheckpoint`** (Django) + LangGraph **checkpointer** for thread continuity across server restarts.

**Speaker note:** “Thin API, fat Modal worker; agent state survives in Postgres/SQLite via checkpoints.”

---

### Slide B — “LangGraph workflow (novel core)”

**Title:** LangGraph agent — `analyze → route → artist → verify`

**Bullets:**

- **analyze (`AnalyzerNode`):** Updates **`SuspectProfile`**, infers **intent** (`generate` / `edit` / `inpaint` / `age`), produces **enhanced_prompt**, **negative_prompt**, **age_params** when applicable.
- **route (`RouterNode`):** Sets **`next_step`** ∈ {`generate`, `edit`, `inpaint`, `age`} from **image presence**, **regenerate phrases**, **aging language**, **facial-region keywords** (eyes, nose, …).
- **artist (`_artist_node`):** Dispatches to **`generate_sketch`**, **`edit_sketch`**, **`inpainting_edit`**, or age path — **local pipeline** or **HTTP to Modal** (`COLAB_ML_URL` / `REMOTE_ML_URL`).
- **verify (`VerificationNode`):** Scores image; calls **forensic critic** if enabled; returns **`end`** or **`retry`** → **artist** again (bounded).

**Figure:** Use `backend-service/ml_engine/smartsketch_agent_graph.mmd` in [mermaid.live](https://mermaid.live) and export PNG for this slide.

---

### Slide C — “Structured suspect profile”

**Title:** From free text to structured forensic brief

**Bullets:**

- **`SuspectProfile` (Pydantic):** Gender, age range, ethnicity, face shape, eyes, hair, facial hair, nose, mouth, **distinctive_features** (glasses, scars, …).
- **`ForensicAgentState`:** Messages (reducer), profile, **current_image** (base64 in checkpoints), **generation_id**, routing flags, **verification_history**, critic fields, **ml_attempt_count**.
- **First-turn prompt fusion:** **`build_initial_generation_prompt`** — witness text + analyzer enhancement + **`profile.to_detailed_prompt()`** wrapped in a **mugshot-style forensic** template for SDXL.

---

### Slide D — “Diffusion pipeline (modalities)”

**Title:** `SmartSketchPipeline` — generation and refinement

**Bullets:**

- **Validate / enhance:** **Qwen2.5-3B-Instruct** (`ForensicPromptValidator`) — case type, age rules, forensic wording; invalid prompts blocked early.
- **Generate:** **SDXL** + optional **LoRA** (strength configurable, e.g. 0.3); steps default **30**; output **photo** then optional **sketch** path (**ControlNet Canny** / simple conversion per `pipeline.py`).
- **Edit:** **SDXL ControlNet Img2Img** + **Canny** structural lock (`FaceEditor`) — identity-aware edits.
- **Inpaint:** **Semantic region** inpainting (`FaceInpainter`) for localized features (eyes, lips, nose, brows, glasses).
- **Restore:** **GFPGAN** optional pass for facial clarity before sketch conversion.
- **Post-process:** **Watermark + hash**; optional **NSFW** image check when safety enabled locally.

---

### Slide E — “Scoring and verification (closed loop)”

**Title:** Quality gate before showing the witness

**Bullets:**

- **`FaceScorer`:** **OpenAI CLIP ViT-B/32** — text–image alignment; **combined_score** = **100 × CLIP** if no identity score, else **100 × (0.6×CLIP + 0.4×identity)**.
- **Identity on edits:** **FaceNet / ArcFace-style** embeddings from **`facenet-pytorch`** in editor path — surfaced as **`identity_score`** / **`last_identity_score`** in API payloads.
- **`VerificationNode`:** If **combined < 50** (and attempts allow) → **`retry`** to artist; if **critic** returns **`revise`** with **`prompt_adjustment`** → one more artist pass with **`critic_adjustment_prompt`** (env: `SMARTSKETCH_ENABLE_FORENSIC_CRITIC`, `SMARTSKETCH_CRITIC_MAX_RETRIES`).
- **Remote mode:** Django agent often has **scorer=None**; Modal may return **`scores`** / **`modal_scores`** — verifier can consume **combined_score** from Modal metadata.

---

### Slide F — “Forensic vision critic (VLM)”

**Title:** Self-hosted forensic critic — Qwen2.5-VL

**Bullets:**

- **Service:** Modal class **`ForensicCriticService`** — default model **`Qwen/Qwen2.5-VL-3B-Instruct`** (env override `SMARTSKETCH_CRITIC_MODEL`).
- **Input:** Witness **profile JSON**, **prompt**, **route_used**, **scores**, image **base64**.
- **Output (parsed JSON):** **`decision`** (`accept` / `revise`), **`issues`**, **`matched_features`**, **`missing_features`**, **`prompt_adjustment`**, **`safety_flags`**, **`reasoning_summary`**.
- **Why it matters:** Bridges **numeric scores** and **witness-facing semantics** (“glasses missing”, “age inconsistent”) for **defensible** iteration.

---

### Slide G — “Modal ML service (deployment truth)”

**Title:** GPU inference on Modal

**Bullets:**

- **Image:** Debian slim, **Python 3.11**, **CUDA 12.4** PyTorch, **diffusers**, **transformers**, **xformers**, **controlnet-aux**, **CLIP** (git), **GFPGAN**, **facenet-pytorch**, **mediapipe**, **invisible-watermark**.
- **Hardware:** **`MODAL_GPU`** (e.g. **L4**); **`timeout`** ~600s; **`scaledown_window`** for cost control.
- **Storage:** **`modal.Volume`** `smartsketch-models` → **`HF_HOME`** on GPU workers for **cached weights**.
- **API:** Fast **`/generate`**, **`/edit`** (internal inpaint vs ControlNet split), **`/age`**, **`/analyze`** (JSON self-healing), **`/critic`**, **`/health`**.

**Update slide 44:** Replace or footnote “Colab” with **“Modal (GPU serverless) + HF volume”** unless you still pay for Colab separately.

---

### Slide H — “Differences: presentation vs implementation (honesty slide)”

**Title:** What we claim vs what we measure

**Bullets:**

- **ArcFace “75% threshold”** in current deck: verify in **`editor.py`** / validator for the **exact** threshold string you show; align slide number with **code or evaluation log**.
- **Colab integration tests** (slide 42): Keep as **prototyping evidence**; clarify **production** path is **Modal + Render + Vercel**.
- **Latency numbers** (~2s Qwen, ~15s SDXL): Treat as **order-of-magnitude**; cite **environment** (GPU type, cold vs warm Modal container).

---

## Expanded detail for your *existing* component slides (merge bullets)

### LLM Validator (your Component 1)

Add:

- JSON-oriented **analyze** path on Modal with **`_analyze_with_self_healing`** — retries if the model returns invalid JSON.
- **Case-type** and **age** constraints in **`ForensicPromptValidator`**.

### Face Generator (Component 2)

Add:

- **Pipeline returns** `generation_id`, **`forensic_hash`**, **`is_watermarked`**, **`scores`**, **`metadata`** to the API layer.
- **Sketch output** branches: **`output_type`** `photo` vs `sketch`, **`sketch_style`**, **`sketch_method`** (`controlnet` vs `simple`).

### Quality Scorer (Component 3)

Add:

- Explicit **60% CLIP / 40% identity** when **`identity_score`** is present.
- **Threshold 50** for automatic **retry** in **`VerificationNode`** (not only “display score”).

### Sketch converter (Component 4)

Add:

- **`MemoryEfficientSketchConverter`** naming in code — worth one bullet for “VRAM-aware design” if asked in Q&A.

### Face editor (Component 5)

Add:

- **ControlNet Canny** for **geometric locking**; **reuse of SDXL weights** from generator to save VRAM (`FaceEditor` constructor path).
- **Distinction:** global **edit_sketch** vs **inpainting_edit** for **local** features — matches your **router** design.

---

## Optional closing bullets for “Future work / limitations”

- Formal **user study** with certified forensic artists; **dataset** and **IRB** if human subjects.
- **Quantitative** identity retention metrics across **long** chat sessions.
- **LangSmith** tracing for viva demos (optional observability).

---

## File references (if examiners ask “where in code?”)

| Concept | Location |
|---------|----------|
| LangGraph graph | `backend-service/ml_engine/agent.py` — `SmartSketchAgent` |
| Router / verifier | `backend-service/ml_engine/agent_nodes.py` |
| State schema | `backend-service/ml_engine/agent_state.py` |
| Pipeline | `backend-service/ml_engine/pipeline.py` |
| Modal service | `backend-service/ml_service/modal_app.py` |
| Mermaid export | `backend-service/ml_engine/smartsketch_agent_graph.mmd` — script `backend-service/scripts/export_langgraph_graph.py` |

---

*Generated to align the defense deck with the SmartSketch workspace as of the project snapshot; adjust numbers and costs to match what you actually run in production and what your institution allows you to claim.*
