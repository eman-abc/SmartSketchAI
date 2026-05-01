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
    .run_commands("apt-get update && apt-get install -y git libgl1 libglib2.0-0 curl")
    .run_commands(
        "pip install --upgrade pip setuptools wheel",
        "pip install numpy==1.26.4",
        "pip install -q Pillow>=10.0.0 requests>=2.28.0 tqdm fastapi uvicorn",
        "pip install -q torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cu121",
        "pip install -q diffusers==0.30.3 transformers==4.44.2 accelerate==0.34.2 safetensors==0.4.4 huggingface_hub==0.25.2 bitsandbytes==0.43.3 xformers",
        "pip install -q controlnet-aux==0.0.9 opencv-python-headless==4.10.0.84 scikit-image==0.24.0 mediapipe invisible-watermark mtcnn",
        "pip install -q langgraph>=1.1.5 langchain-core>=1.2.10 pydantic>=2.0",
        "pip install -q gfpgan facexlib basicsr",
        "pip install -q facenet-pytorch --no-deps",
        "pip install -q git+https://github.com/openai/CLIP.git",
        "mkdir -p /models && curl -L -o /models/GFPGANv1.4.pth https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/GFPGANv1.4.pth",
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
            enable_sketch=True,
            enable_editing=True,
            enable_inpainting=True,
            enable_restoration=True,
        )
        print("[SmartSketch] ✅ All models loaded in-memory (SDXL, Qwen, CLIP, GFPGAN)")

    # ─────────────────────────────────────────────────────────────────────────
    @modal.method()
    def generate(self, body: dict) -> dict:
        prompt    = body.get("prompt", "")
        negative  = body.get("negative_prompt")
        case_type = body.get("case_type", "criminal")
        age       = int(body.get("age", 30))
        seed      = body.get("seed")

        result = self.pipeline.generate_sketch(
            prompt=prompt,
            negative_prompt=negative,
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
                negative_prompt=body.get("negative_prompt"),
                strength=0.80,
                age=age,
            )
        else:
            result = self.pipeline.edit_sketch(
                generation_id=generation_id,
                original_image=original_image,
                edit_prompt=edit_prompt,
                negative_prompt=body.get("negative_prompt"),
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

    # ─────────────────────────────────────────────────────────────────────────
    @modal.method()
    def age(self, body: dict) -> dict:
        generation_id   = body.get("generation_id", "unknown")
        original_b64    = body.get("original_image", "")
        years           = int(body.get("years", 0))
        enhanced_prompt = body.get("prompt") # The analyzer-enhanced age prompt
        seed            = body.get("seed")

        if not original_b64:
            return {"success": False, "error": "original_image is required"}

        original_image = _b64_to_pil(original_b64)

        result = self.pipeline.age_progression(
            generation_id=generation_id,
            original_image=original_image,
            years=years,
            enhanced_prompt=enhanced_prompt,
            seed=seed
        )

        if not result.get("success"):
            return {"success": False, "error": result.get("error", "Age progression failed")}

        return {
            "success":        True,
            "edited_image":   _pil_to_b64(result["edited_image"]),
            "edit_id":        result.get("edit_id", ""),
            "identity_score": result.get("identity_score", 0.0),
            "scores":         result.get("scores", {}),
            "years":          years,
        }

    # ─────────────────────────────────────────────────────────────────────────
    @modal.method()
    def analyze(self, body: dict) -> dict:
        """
        Uses the on-GPU Qwen model to perform forensic analysis and routing.
        Acts as a high-reliability fallback for Gemini.
        """
        system_prompt = body.get("system_prompt")
        user_message  = body.get("user_message")

        if not system_prompt or not user_message:
            return {"success": False, "error": "system_prompt and user_message required"}

        try:
            # Use the already loaded validator (Qwen 3B) for general LLM tasks
            response = self.pipeline.validator._call_llm(system_prompt, user_message)
            return {
                "success":  True,
                "response": response,
                "model":    "qwen-2.5-3b-fallback"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


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

    @web_app.post("/age")
    async def age(request: Request):
        body   = await request.json()
        result = service.age.remote(body)
        return JSONResponse(result)

    @web_app.post("/analyze")
    async def analyze(request: Request):
        body   = await request.json()
        result = service.analyze.remote(body)
        return JSONResponse(result)

    return web_app


# ── 8. Optional: keep-warm cron (prevents cold starts during business hours) ──
# @app.function(schedule=modal.Cron("*/15 8-22 * * 1-6"))  # every 15 min, weekdays+Sat
def keep_warm():
    """Pings the service to keep the container alive during peak hours."""
    SmartSketchService().generate.remote({
        "prompt": "warmup ping", "case_type": "missing", "age": 25
    })
    print("[keep_warm] Container is warm ✅")
