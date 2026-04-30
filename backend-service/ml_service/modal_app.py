"""
SmartSketch ML Service — Modal.com Serverless Deployment
Exposes /generate and /edit as persistent HTTPS endpoints,
fully compatible with Django's COLAB_ML_URL env var pattern.

Deploy:
    pip install modal
    modal token new
    modal deploy ml_service/modal_app.py

Set in Render env vars:
    COLAB_ML_URL=<url printed by modal deploy>
"""

import io
import base64
import modal
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# ── 1. Docker image with all ML dependencies ─────────────────────────────────
from pathlib import Path
LOCAL_ML_ENGINE = Path(__file__).parent.parent / "ml_engine"

image = (
    modal.Image.debian_slim(python_version="3.11")
    .run_commands("apt-get update && apt-get install -y git libgl1 libglib2.0-0")
    .pip_install(
        "numpy==1.26.4",
        "Pillow>=10.0.0",
    )
    .pip_install(
        "torch==2.5.1",
        "torchvision==0.20.1",
        "xformers",
        extra_index_url="https://download.pytorch.org/whl/cu121",
    )
    .pip_install(
        "diffusers==0.30.3",
        "transformers==4.44.2",
        "accelerate==0.34.2",
        "safetensors==0.4.4",
        "huggingface_hub==0.25.2",
        "bitsandbytes==0.43.3",
        "controlnet-aux==0.0.9",
        "opencv-python-headless==4.10.0.84",
        "scikit-image==0.24.0",
        "mediapipe",
        "invisible-watermark",
        "langgraph>=1.1.5",
        "langchain-core>=1.2.10",
        "pydantic>=2.0",
        "fastapi",
        "uvicorn",
    )
    .run_commands(
        "pip install git+https://github.com/openai/CLIP.git",
        "pip install facenet-pytorch --no-deps",
        "pip install mtcnn",
    )
    .add_local_dir(
        LOCAL_ML_ENGINE,
        remote_path="/root/ml_engine"
    )
)

# ── 3. Persistent volume — model weights survive container restarts ───────────
volume = modal.Volume.from_name("smartsketch-models", create_if_missing=True)
MODEL_DIR = "/models"

# ── 4. Modal app ─────────────────────────────────────────────────────────────
app = modal.App("smartsketch-ml", image=image)

web_app = FastAPI(title="SmartSketch ML API")


# ── 5. GPU inference class ────────────────────────────────────────────────────
@app.cls(
    gpu="T4",                          # cheapest Modal GPU ~$0.001/sec
    volumes={MODEL_DIR: volume},
    timeout=300,
    scaledown_window=120,        # keep warm 2 min between requests
)
class SmartSketchService:

    @modal.enter()
    def load_pipeline(self):
        """Runs once when the container starts. Loads all model weights."""
        import sys
        import os

        if "/root" not in sys.path:
            sys.path.insert(0, "/root")

        # Point HuggingFace cache to the persistent volume
        os.environ["HF_HOME"]            = MODEL_DIR
        os.environ["TRANSFORMERS_CACHE"] = MODEL_DIR
        os.environ["DIFFUSERS_CACHE"]    = MODEL_DIR

        print("[SmartSketch] Loading pipeline …")
        from ml_engine.pipeline import SmartSketchPipeline

        self.pipeline = SmartSketchPipeline.from_pretrained(
            lora_path=None,
            device="cuda",
            enable_offload=True,
        )
        print("[SmartSketch] ✅ Pipeline ready")

    # ─────────────────────────────────────────────────────────────────────────
    @modal.method()
    def generate(self, body: dict) -> dict:
        prompt    = body.get("prompt", "")
        case_type = body.get("case_type", "criminal")
        age       = int(body.get("age", 30))
        seed      = body.get("seed")

        result = self.pipeline.generate_sketch(
            prompt=prompt,
            case_type=case_type,
            age=age,
            seed=seed,
            output_type="photo",
        )

        if not result.get("success"):
            return {"success": False, "error": result.get("error", "Generation failed")}

        img_b64 = _pil_to_b64(result["image"])

        return {
            "success":       True,
            "image_base64":  img_b64,
            "generation_id": result["generation_id"],
            "forensic_hash": result["forensic_hash"],
            "scores":        result["scores"],
            "metadata":      result["metadata"],
        }

    # ─────────────────────────────────────────────────────────────────────────
    @modal.method()
    def edit(self, body: dict) -> dict:
        generation_id = body.get("generation_id", "unknown")
        original_b64  = body.get("original_image", "")
        edit_prompt   = body.get("edit_prompt", "")
        strength      = float(body.get("strength", 0.65))
        age           = int(body.get("age", 30))

        if not original_b64 or not edit_prompt:
            return {"success": False, "error": "original_image and edit_prompt are required"}

        original_image = _b64_to_pil(original_b64)

        # Smart routing: inpaint for eye/face-region edits, ControlNet for the rest
        INPAINT_KW = ["eye", "glass", "spectac", "lip", "mouth", "nose", "brow"]
        use_inpaint = any(kw in edit_prompt.lower() for kw in INPAINT_KW)

        if use_inpaint:
            result  = self.pipeline.inpainting_edit(
                generation_id=generation_id,
                original_image=original_image,
                edit_prompt=edit_prompt,
                strength=0.80,
                age=age,
            )
        else:
            result = self.pipeline.edit_sketch(
                generation_id=generation_id,
                original_image=original_image,
                edit_prompt=edit_prompt,
                strength=strength,
            )

        if not result.get("success"):
            return {"success": False, "error": result.get("error", "Edit failed")}

        return {
            "success":        True,
            "edited_image":   _pil_to_b64(result["edited_image"]),
            "edit_id":        result.get("edit_id", ""),
            "identity_score": result.get("identity_score", 0.0),
            "scores":         result.get("scores", {}),
            "route_used":     "inpaint" if use_inpaint else "controlnet",
        }


# ── 6. Helper serializers ─────────────────────────────────────────────────────
def _pil_to_b64(img) -> str:
    from PIL import Image
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def _b64_to_pil(b64: str):
    from PIL import Image
    return Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB")


# ── 7. FastAPI ASGI endpoint (replaces Colab Flask server) ───────────────────
@app.function()
@modal.asgi_app()
def fastapi_app():
    service = SmartSketchService()

    @web_app.get("/health")
    async def health():
        return {"status": "ok", "pipeline": "loaded"}

    @web_app.post("/generate")
    async def generate(request: Request):
        body   = await request.json()
        result = service.generate.remote(body)
        return JSONResponse(result)

    @web_app.post("/edit")
    async def edit(request: Request):
        body   = await request.json()
        result = service.edit.remote(body)
        return JSONResponse(result)

    return web_app


# ── 8. Optional: keep-warm cron (prevents cold starts during business hours) ──
@app.function(schedule=modal.Cron("*/15 8-22 * * 1-6"))  # every 15 min, weekdays+Sat
def keep_warm():
    """Pings the service to keep the container alive during peak hours."""
    SmartSketchService().generate.remote({
        "prompt": "warmup ping", "case_type": "missing", "age": 25
    })
    print("[keep_warm] Container is warm ✅")
