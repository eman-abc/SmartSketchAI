# SmartSketch.AI

SmartSketch.AI is a full-stack forensic facial composite platform that turns natural-language witness descriptions into iterative, refinable suspect portraits. Investigators interact through a chat-first interface while a LangGraph agent on the backend interprets each turn, routes to the appropriate generative tool, verifies output quality, and persists session state across restarts. Heavy GPU inference runs on Modal; the web API stays thin on Render; the React client ships on Vercel.

This repository is the capstone implementation for a Bachelor of Engineering in Software Engineering project. It is designed as a production-shaped system: JWT authentication, audit hooks, structured agent state, serverless GPU workers, and explicit separation between orchestration policy and pixel synthesis.

---

## Table of contents

1. [Problem](#problem)
2. [Solution](#solution)
3. [System architecture](#system-architecture)
4. [Technology stack](#technology-stack)
5. [Engineering decisions](#engineering-decisions)
6. [Frontend and user experience](#frontend-and-user-experience)
7. [Backend and API](#backend-and-api)
8. [AI and machine learning](#ai-and-machine-learning)
9. [Deployment](#deployment)
10. [Repository layout](#repository-layout)
11. [Local development](#local-development)
12. [Environment variables](#environment-variables)
13. [API overview](#api-overview)
14. [Further documentation](#further-documentation)

---

## Problem

Traditional forensic sketching depends on trained artists, long session times, and subjective interpretation. Witness interviews are incremental: a description is rarely complete in one utterance. Investigators need to refine eyes, hair, jaw structure, age, and distinctive marks without losing identity or restarting from scratch.

A single-shot text-to-image tool does not match that workflow. It cannot reliably decide when to regenerate entirely, when to edit globally, when to inpaint a facial region, or when to apply age progression. It also lacks structured memory of what the witness has already asserted, auditable persistence, and deployment boundaries suitable for a CPU-only API tier plus a GPU inference tier.

---

## Solution

SmartSketch packages forensic composite work as a **stateful conversational agent** backed by a **multi-stage generative pipeline**:

- **Structured suspect memory** (`SuspectProfile`) accumulates attributes across chat turns.
- **LangGraph orchestration** runs `analyze → route → artist → verify` with bounded retries when scores or a vision critic request revision.
- **Tool routing** selects among full generation (SDXL), ControlNet img2img edit, semantic region inpainting, and aging.
- **Quality gates** combine CLIP semantic alignment, optional FaceNet-style identity scoring, and an optional Qwen2.5-VL forensic critic.
- **Integrity layer** applies invisible watermarking (DWT-DCT via `invisible-watermark`) and SHA-256 content hashing on pipeline outputs.
- **Three-tier deployment** keeps the browser thin, Django as policy and persistence, and Modal as the GPU worker.

The primary user surface is **chat**: login, describe a suspect, refine in follow-up messages, optionally switch sketch modality or aging from the side panel, and review pipeline status in a forensic console during long GPU runs.

---

## System architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Tier 1: Client (Vercel)                                                │
│  React 19 · TypeScript · Vite · Tailwind                                │
│  JWT in browser storage · fetch + SSE for agent stream                  │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │ HTTPS  /api/*
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Tier 2: Application (Render)                                           │
│  Django REST · simplejwt · PostgreSQL (prod) / SQLite (local)           │
│  LangGraph agent · media uploads · audit / forensic request models      │
│  CPU-only in production (USE_LOCAL_ML=False)                              │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │ HTTPS JSON (base64 images)
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Tier 3: ML inference (Modal)                                           │
│  FastAPI ASGI · GPU class (e.g. L4) · persistent HF volume              │
│  SmartSketchPipeline · ForensicCriticService                            │
│  /generate · /edit · /age · /analyze · /critic · /health              │
└─────────────────────────────────────────────────────────────────────────┘
```

**Typical request path (agent chat):**

1. Browser posts to `/api/forensic/chat/stream/` with Bearer JWT and `thread_id`.
2. Django invokes `SmartSketchAgent.run()`; LangGraph checkpoints state in `AgentCheckpoint`.
3. Analyzer updates profile and intent; router sets `next_step`; artist calls Modal.
4. Modal runs the appropriate pipeline stage and returns JSON with base64 image and scores.
5. Verifier scores output and may loop to artist with critic adjustments (bounded).
6. Django persists `GeneratedImage`, scores, and critique rows; responds with SSE events and a result payload (including inline PNG data URLs for reliable SPA rendering).

---

## Technology stack

| Layer | Technologies | Role |
|-------|----------------|------|
| **Frontend** | React 19, TypeScript, Vite 7, Tailwind CSS 3, React Router 7, Vitest | SPA, chat workspace, sketch controls, forensic console |
| **API** | Django 5.x, Django REST Framework, simplejwt, django-cors-headers, WhiteNoise, Gunicorn | REST, auth, orchestration, persistence |
| **Database** | PostgreSQL (Render), SQLite (local), dj-database-url | Users, images, scores, agent checkpoints, audit |
| **Agent** | LangGraph, langchain-core, Pydantic | Stateful graph, `SuspectProfile`, checkpointing |
| **ML runtime** | PyTorch, Hugging Face Diffusers, Transformers, xformers, accelerate | SDXL, ControlNet, inpainting, Qwen, VLM critic |
| **ML models** | SDXL 1.0, Qwen2.5-3B-Instruct, Qwen2.5-VL-3B-Instruct, OpenAI CLIP ViT-B/32, optional LoRA | Generation, validation, critique, scoring |
| **CV / faces** | controlnet-aux, OpenCV, MediaPipe, facenet-pytorch, scikit-image | Canny control, masks, identity embeddings, SSIM fallback |
| **Restoration** | GFPGAN, facexlib, basicsr | Optional face clarity pass |
| **Integrity** | invisible-watermark, hashlib (SHA-256) | Watermark and content fingerprint |
| **ML hosting** | Modal, FastAPI, uvicorn | Serverless GPU containers and HTTP endpoints |
| **CI** | GitHub Actions | Modal deploy on `ml_engine` / `ml_service` changes; health pings |

---

## Engineering decisions

**Thin API, fat GPU worker.** Production Django never loads Torch weights unless `USE_LOCAL_ML=True` (local GPU development only). All diffusion and vision-language inference runs on Modal. This keeps Render memory predictable and allows ML image iteration without redeploying the full monolith.

**LangGraph instead of ad-hoc imperative routing.** Witness workflows are graphs: branch on intent, loop on verification, persist checkpoints. Encoding `analyze → route → artist → verify` as an explicit graph makes behavior reviewable, testable, and defensible in academic review.

**Structured profile vs. ever-growing prompt strings.** `SuspectProfile` (Pydantic) merges incremental witness facts and exposes `to_detailed_prompt()` for SDXL conditioning. Negative prompt sanitization avoids negating traits already asserted in the profile.

**Multiple edit modalities.** Global structural changes use ControlNet img2img with Canny edges. Localized features (eyes, nose, glasses) route to SDXL inpainting with MediaPipe-derived masks. Aging uses a dedicated editor path with lower IP-Adapter scale to allow temporal change while locking bone structure.

**Closed-loop quality.** `VerificationNode` combines numeric scores (CLIP plus optional identity) with an optional self-hosted VLM critic that returns JSON with `accept` or `revise` and `prompt_adjustment`. Retries are capped via `MAX_RETRIES` and `SMARTSKETCH_CRITIC_MAX_RETRIES`.

**Production image delivery.** Agent chat can return inline `data:image/png;base64,...` URLs so the SPA renders composites on HTTPS without depending solely on `/media/` URL routing or mixed-content edge cases. Media files are still stored for history and REST endpoints.

**Forensic policy in the validator layer.** `ForensicPromptValidator` (Qwen2.5-3B-Instruct) returns structured JSON for validity and enhancement. Hardcoded safety rules and a forensic override list accept legitimate witness language (skin texture, stubble, jaw changes) that an overcautious LLM might reject.

---

## Frontend and user experience

**Location:** `frontend-app/frontend/`

The UI is intentionally minimal: authentication pages and a single forensic studio workspace. The layout follows a three-column pattern:

| Area | Components | Purpose |
|------|------------|---------|
| **Left** | `Sidebar` | Session artifacts (prior generations in the thread), navigation |
| **Center** | `Workspace` | Chat transcript, example prompts, progress bar, rendered composite cards per assistant turn |
| **Right** | `RightPanel` | Live sketch preview, sketch mode (photo / pencil / charcoal / forensic), aging slider, pipeline step indicators, `ForensicConsole` logs |

**Interaction model:**

- **Chat** is the primary creative surface. Each user message triggers the LangGraph agent via streaming SSE (`agentChatStream` in `lib/api.ts`) so the forensic console shows analyzer, route, artist, and verify stages during GPU latency.
- **JWT** access and refresh tokens live in `authStore`; `api.ts` retries once on 401 with refresh, then redirects to login.
- **Session continuity** uses a client-generated `thread_id` per workspace session so agent checkpoints align with backend persistence.
- **Right panel** exposes non-chat actions: sketch style conversion (`/forensic/sketch-style/`), aging progression (`/forensic/age/`), and PDF export (`/forensic/export-report/`) without replacing the chat-first narrative.

**Styling:** Dark forensic studio theme via Tailwind; responsive glass panels and monospace generation IDs for traceability.

---

## Backend and API

**Location:** `backend-service/`

Django exposes a REST API under `/api/` with JWT authentication on protected routes. Key domains:

| Domain | Models / behavior |
|--------|-------------------|
| **Auth** | Custom `User` with roles (admin, forensic, editor, general); register, token, refresh |
| **Images** | `GeneratedImage`, `EditedImage`, `ImageScore`, `ForensicCritique` |
| **Agent** | `Conversation`, `AgentCheckpoint` (LangGraph serialized state by `thread_id`) |
| **Governance** | `AuditLog`, `ForensicRequest` (approval workflow hooks) |

**ML gateway:** `api/ml_service.py` provides `MLService.get_agent()` for chat and optionally `get_pipeline()` when `USE_LOCAL_ML=True`. The agent's artist node POSTs to Modal (`/generate`, `/edit`, `/age`) with normalized base URLs and passes `target_region`, `age`, and edit strength when routed from LangGraph.

**Media:** `MEDIA_ROOT` stores uploaded composites; `urls.py` serves `/media/` in all environments. On Render, `SECURE_PROXY_SSL_HEADER` ensures absolute URLs use HTTPS.

**Container:** `Dockerfile` plus `entrypoint.sh` for Render deploy; `render.yaml` defines web service and managed Postgres.

See `backend-service/API_INTEGRATION_SPEC.md` for request and response shapes.

---

## AI and machine learning

**Location:** `backend-service/ml_engine/` (shared with Modal image via `ml_service/modal_app.py`)

### SmartSketchPipeline stages

1. **Validate / enhance** (`ForensicPromptValidator`, Qwen2.5-3B-Instruct): safety, case type, forensic wording, JSON output with enhanced prompt.
2. **Generate** (`FaceGenerator`, SDXL + optional LoRA): single image per call (`num_images_per_prompt=1`); strong negative prompts against collage and multi-face layouts.
3. **Edit** (`FaceEditor`, SDXL ControlNet img2img + Canny): geometry-stable global edits; FaceNet embeddings for identity score.
4. **Inpaint** (`FaceInpainter`, SDXL inpainting + `FaceMasker` / MediaPipe): region-targeted changes.
5. **Age** (`FaceEditor.age_edit`): temporal progression with tuned IP-Adapter scale.
6. **Optional sketch** (`MemoryEfficientSketchConverter`): pencil / charcoal / forensic styling.
7. **Optional restore** (`FaceRestorer`, GFPGAN): facial clarity before downstream steps.
8. **Integrity** (`ForensicSigner`): invisible watermark (`SMARTSKETCH_AI`, DWT-DCT) and SHA-256 hash over pixel bytes.
9. **Score** (`FaceScorer`, CLIP ViT-B/32): combined score (60% CLIP + 40% identity when identity scalar present).

### LangGraph agent (`ml_engine/agent.py`)

| Node | Responsibility |
|------|----------------|
| **analyze** | Update `SuspectProfile`, intent, enhanced/negative prompts, age params; fallback chain: LLM → Modal `/analyze` → heuristics |
| **route** | Set `next_step`: generate, edit, inpaint, age from image presence, regenerate phrases, region keywords |
| **artist** | Dispatch to pipeline or Modal HTTP; increment `ml_attempt_count` |
| **verify** | CLIP/identity scoring, optional VLM critic, retry or end |

Static graph export: `python backend-service/scripts/export_langgraph_graph.py` → `ml_engine/smartsketch_agent_graph.mmd`.

### Modal service endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Liveness and pipeline loaded check |
| `POST /generate` | Full forensic generation |
| `POST /edit` | ControlNet or inpaint (keyword / `target_region` routing) |
| `POST /age` | Age progression / regression |
| `POST /analyze` | JSON profile and intent for analyzer fallback |
| `POST /critic` | Qwen2.5-VL forensic vision critique |

Deploy: `modal deploy backend-service/ml_service/modal_app.py` (requires Modal token and Hugging Face secret on Modal).

---

## Deployment

| Component | Platform | Notes |
|-----------|----------|-------|
| **Frontend** | Vercel | `VITE_API_BASE_URL` points to Render API; `vercel.json` for SPA routing |
| **Backend** | Render | Docker web service `smartsketch-api`, Postgres `smartsketch-db`, `DEBUG=False` |
| **ML** | Modal | GPU class, `smartsketch-models` volume for HF cache; CI via `.github/workflows/modal.yml` |

**Wiring:**

- Frontend production env: `frontend-app/frontend/.env.production` → `https://smartsketch-api.onrender.com/api` (adjust to your Render hostname).
- Backend: set `COLAB_ML_URL` to Modal HTTPS base (historical name; value is the Modal app URL). `REMOTE_ML_URL` optionally overrides for the agent.
- CORS allowlist includes Vercel hostnames and local dev ports in `settings.py`.

**CI workflows:** `frontend.yml` and `backend.yml` ping deployed URLs after push; `modal.yml` deploys ML on changes to `ml_service` or `ml_engine` on `main` / `ml-integration`.

---

## Repository layout

```
SmartSketch_Workspace/
├── frontend-app/frontend/     React SPA (Vite)
├── backend-service/
│   ├── api/                     Django app: views, models, serializers, URLs
│   ├── ml_engine/               Pipeline, agent, nodes, scorer, integrity
│   ├── ml_service/              Modal app (modal_app.py)
│   ├── smartsketch_backend/     Django project settings
│   ├── scripts/                 Utilities (e.g. LangGraph Mermaid export)
│   ├── Dockerfile               Render container
│   └── API_INTEGRATION_SPEC.md
├── docs/                        Defense narratives, architecture supplements
├── .github/workflows/           CI: frontend, backend, Modal
└── render.yaml                  Render Blueprint (API + Postgres)
```

---

## Local development

### Prerequisites

- Python 3.10+
- Node.js 18+ (for frontend)
- Optional: NVIDIA GPU + `USE_LOCAL_ML=True` for local pipeline without Modal
- Optional: Modal account and CLI for remote ML

### Backend

```bash
cd backend-service
python -m venv venv
# Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Set COLAB_ML_URL to your Modal service URL
python manage.py migrate
python manage.py runserver
```

API base: `http://127.0.0.1:8000/api`

### Frontend

```bash
cd frontend-app/frontend
npm install
cp .env.example .env
# VITE_API_BASE_URL=http://127.0.0.1:8000/api
npm run dev
```

### Modal (ML worker)

```bash
pip install modal
modal token new
modal deploy backend-service/ml_service/modal_app.py
```

Copy the printed HTTPS URL into `COLAB_ML_URL` in backend `.env`.

---

## Environment variables

### Backend (`backend-service/.env`)

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Django secret (required in production) |
| `DEBUG` | `True` local, `False` on Render |
| `DATABASE_URL` | Postgres on Render; omit for local SQLite default |
| `COLAB_ML_URL` | Modal ML service HTTPS URL (e.g. `.../generate` or base; normalized in code) |
| `REMOTE_ML_URL` | Optional override for agent; defaults to `COLAB_ML_URL` |
| `USE_LOCAL_ML` | `True` only with local GPU to load pipeline on Django |
| `SMARTSKETCH_ENABLE_FORENSIC_CRITIC` | Enable VLM critic in verifier (default `True`) |
| `SMARTSKETCH_CRITIC_MODEL` | Default `Qwen/Qwen2.5-VL-3B-Instruct` |
| `SMARTSKETCH_IDENTITY_PRESERVED_THRESHOLD` | Identity pass threshold for editor metadata (default `0.55`) |
| `SMARTSKETCH_CONTROLNET_CONDITIONING_SCALE` | ControlNet lock strength (default `0.65`) |

### Frontend (`frontend-app/frontend/.env`)

| Variable | Description |
|----------|-------------|
| `VITE_API_BASE_URL` | Django API prefix, e.g. `http://127.0.0.1:8000/api` |

---

## API overview

All paths are relative to `/api/`.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/register/` | No | Create account |
| POST | `/token/` | No | Obtain JWT access + refresh |
| POST | `/token/refresh/` | No | Refresh access token |
| GET | `/profile/` | Yes | Current user profile |
| GET | `/my-images/` | Yes | User's generated images |
| GET | `/audit-logs/` | Yes | Audit trail (admin-oriented) |
| POST | `/forensic/generate/` | Yes | Stateless generate from prompt |
| POST | `/forensic/edit/` | Yes | Edit by `original_image_id` |
| POST | `/forensic/age/` | Yes | Age progression by image id |
| POST | `/forensic/chat/` | Yes | Stateful agent (JSON response) |
| POST | `/forensic/chat/stream/` | Yes | Agent with SSE status + result |
| POST | `/forensic/sketch-style/` | Yes | Convert style (pencil / charcoal / forensic) |
| POST | `/forensic/export-report/` | Yes | PDF forensic report |
| GET | `/health/` | No | API health check |

Full schemas: `backend-service/API_INTEGRATION_SPEC.md`.

---

## Further documentation

| Document | Contents |
|----------|----------|
| `docs/FYP_DEFENSE_DEEP_NARRATIVE.md` | End-to-end defense narrative, LangGraph rationale |
| `docs/FYP_SYSTEM_ARCHITECTURE_FOR_SLIDES.md` | Architecture summary, Mermaid diagrams, slide outline |
| `docs/FINAL_DEFENSE_AI_ML_SUPPLEMENT.md` | ML component mapping and novelty bullets |
| `backend-service/README_BACKEND.md` | Short backend quickstart |
| `backend-service/ml_engine/smartsketch_agent_graph.mmd` | LangGraph Mermaid export |

---

## Team

Final Year Project, National University of Science and Technology (NUST), Islamabad.

**Contributors:** Muqaddas Anees, Muqadas Zahra, Eman Chaudhary

---

## License

Academic project repository. Contact the authors for reuse terms.
