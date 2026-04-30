# SmartSketch: Backend & Architectural Audit

This document outlines critical structural issues and production-readiness risks identified during the Principal Architect audit.

## 🚨 Critical Breaking Points

### 1. Synchronous Request Blocking
- **Issue:** The `agent_chat` view executes heavy ML inference directly within the HTTP request/response cycle.
- **Risk:** SDXL/Qwen inference takes ~20-40 seconds. Gunicorn workers will block, and browsers/Nginx will timeout after 30 seconds, leading to a "ghost" system where the GPU works while the user sees a 504 error.
- **Immediate Fix:** Implement **Celery & Redis** for asynchronous task execution. Return a `task_id` and poll for results.

### 2. Insecure Serialization (RCE Risk)
- **Issue:** `DjangoCheckpointer` uses Python's `pickle` to serialize and deserialize agent states from the database.
- **Risk:** `pickle` is inherently insecure. If the database is compromised (via SQL Injection or unauthorized access), an attacker can inject malicious blobs that execute arbitrary code when loaded by the agent.
- **Immediate Fix:** Switch to **JSON** or **orjson** for state serialization.

### 3. SQLite Concurrency (Database Locking)
- **Issue:** LangGraph agents perform frequent writes (`put_writes`). Even with WAL mode enabled, SQLite's file-level locking is a bottleneck.
- **Risk:** Concurrent investigator sessions will trigger `OperationalError: database is locked`.
- **Immediate Fix:** Migrate to **PostgreSQL** for row-level locking and enterprise-grade concurrency.

## 🏗️ Architectural Inconsistencies

### 1. Monolithic Inference
- **Issue:** The API server and ML models run in the same process via `MLService`.
- **Risk:** A single GPU Out-of-Memory (OOM) error crashes the entire backend API, preventing users from even logging in or viewing logs.
- **Recommendation:** Decouple ML inference into a separate microservice (e.g., FastAPI on a GPU node).

### 2. Singleton Thread-Safety
- **Issue:** `MLService` uses class-level singletons (`_pipeline`, `_agent`).
- **Risk:** Parallel requests will access the same PyTorch pipeline instance, which can lead to state corruption or race conditions in the GPU VRAM.
- **Recommendation:** Implement a proper **Inference Queue** to serialize access to the GPU.

## 📈 Scaling & Optimization

- **Media Storage:** Current images are stored locally or in SQLite. Move to **AWS S3 / Azure Blob** with lifecycle policies.
- **Observability:** Lack of telemetry for GPU temperature, VRAM usage, and inference latency. Integrate **Prometheus** or **WandB** for production monitoring.
