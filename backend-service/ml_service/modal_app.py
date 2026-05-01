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
import gc
import json
import os
import re
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
        "pip install -q 'transformers>=4.51.0' qwen-vl-utils",
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
    gpu=os.environ.get("MODAL_GPU", "L4"),
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
        try:
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
                "is_watermarked": result.get("is_watermarked", True),
                "scores":        result["scores"],
                "metadata":      result["metadata"],
            }
        finally:
            _cleanup_cuda()

    # ─────────────────────────────────────────────────────────────────────────
    @modal.method()
    def edit(self, body: dict) -> dict:
        try:
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
                "forensic_hash":  result.get("forensic_hash"),
                "is_watermarked": result.get("is_watermarked", True),
                "scores":         result.get("scores", {}),
                "route_used":     "inpaint" if use_inpaint else "controlnet",
            }
        finally:
            _cleanup_cuda()

    # ─────────────────────────────────────────────────────────────────────────
    @modal.method()
    def age(self, body: dict) -> dict:
        try:
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
                "forensic_hash":  result.get("forensic_hash"),
                "is_watermarked": result.get("is_watermarked", True),
                "scores":         result.get("scores", {}),
                "years":          years,
            }
        finally:
            _cleanup_cuda()

    # ─────────────────────────────────────────────────────────────────────────
    @modal.method()
    def analyze(self, body: dict) -> dict:
        """
        Uses the on-GPU Qwen model to perform forensic analysis and routing.
        Acts as the self-hosted text LLM fallback for semantic routing.
        """
        try:
            system_prompt = body.get("system_prompt")
            user_message  = body.get("user_message")

            if not system_prompt or not user_message:
                return {"success": False, "error": "system_prompt and user_message required"}

            try:
                response = self._analyze_with_self_healing(system_prompt, user_message)
                if response is None:
                    return {"success": False, "error": "Unable to produce valid JSON after retries"}

                return {
                    "success":  True,
                    "response": response,
                    "model":    "qwen-2.5-3b-fallback"
                }
            except Exception as e:
                return {"success": False, "error": str(e)}
        finally:
            _cleanup_cuda()

    def _analyze_with_self_healing(self, system_prompt: str, user_message: str, max_retries: int = 3) -> str | None:
        """Call the local validator and retry if the response cannot be parsed as valid JSON."""
        prompt = user_message

        for attempt in range(1, max_retries + 1):
            response = self.pipeline.validator._call_llm(system_prompt, prompt)
            candidate = self._extract_valid_json(response)
            if candidate is not None:
                return candidate

            if attempt < max_retries:
                prompt = (
                    "The previous response was not valid JSON. "
                    f"Please reply with only valid JSON matching the expected schema.\n"
                    "Do not include any markdown fences, explanatory text, or code blocks.\n"
                    "Here is the original user message:\n"
                    f"{user_message}\n"
                    "Previous invalid response:\n"
                    f"{response}\n"
                )

        return None

    def _extract_valid_json(self, text: str) -> str | None:
        """Extract and normalize the first valid JSON object from the LLM text."""
        cleaned = text.strip()
        cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\s*```$', '', cleaned, flags=re.IGNORECASE)

        candidates = self._find_json_objects(cleaned)
        if not candidates:
            candidates = [cleaned]

        for candidate in candidates:
            candidate = self._normalize_json_text(candidate)
            try:
                json.loads(candidate)
                return candidate
            except json.JSONDecodeError:
                continue

        return None

    def _find_json_objects(self, text: str) -> list[str]:
        """Find balanced JSON object substrings in the text."""
        candidates = []
        depth = 0
        start = None
        for idx, char in enumerate(text):
            if char == '{':
                if depth == 0:
                    start = idx
                depth += 1
            elif char == '}' and depth > 0:
                depth -= 1
                if depth == 0 and start is not None:
                    candidates.append(text[start:idx + 1])
                    start = None

        return candidates

    def _normalize_json_text(self, text: str) -> str:
        """Remove common JSON formatting issues from LLM output."""
        text = re.sub(r',\s*([\]}])', r'\1', text)
        text = text.strip()
        return text


@app.cls(
    gpu=os.environ.get("MODAL_CRITIC_GPU", os.environ.get("MODAL_GPU", "L4")),
    volumes={MODEL_DIR: volume},
    timeout=180,
    scaledown_window=120,
)
class ForensicCriticService:
    @modal.enter()
    def load_model(self):
        import torch
        from transformers import AutoProcessor

        model_name = os.environ.get("SMARTSKETCH_CRITIC_MODEL", "Qwen/Qwen2.5-VL-3B-Instruct")
        os.environ["HF_HOME"] = MODEL_DIR
        os.environ["TRANSFORMERS_CACHE"] = MODEL_DIR

        print(f"[ForensicCritic] Loading {model_name}...")
        self.model_name = model_name
        self.processor = AutoProcessor.from_pretrained(model_name, trust_remote_code=True)

        try:
            from transformers import Qwen2_5_VLForConditionalGeneration
            model_cls = Qwen2_5_VLForConditionalGeneration
        except Exception:
            from transformers import AutoModelForVision2Seq
            model_cls = AutoModelForVision2Seq

        self.model = model_cls.from_pretrained(
            model_name,
            torch_dtype=torch.float16,
            device_map="auto",
            trust_remote_code=True,
            low_cpu_mem_usage=True,
        )
        print("[ForensicCritic] Vision critic ready")

    @modal.method()
    def analyze(self, body: dict) -> dict:
        try:
            image_b64 = body.get("image_base64", "")
            if not image_b64:
                return {"success": False, "error": "image_base64 is required"}

            image = _b64_to_pil(image_b64)
            prompt = _build_critic_prompt(body)
            raw_response = self._infer(image, prompt)
            critic_report = _parse_critic_json(raw_response)
            critic_report["model"] = self.model_name
            return {"success": True, "critic_report": critic_report}
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            _cleanup_cuda()

    def _infer(self, image, prompt: str) -> str:
        import torch

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": prompt},
                ],
            }
        ]
        text = self.processor.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )

        try:
            from qwen_vl_utils import process_vision_info
            image_inputs, video_inputs = process_vision_info(messages)
            inputs = self.processor(
                text=[text],
                images=image_inputs,
                videos=video_inputs,
                padding=True,
                return_tensors="pt",
            )
        except Exception:
            inputs = self.processor(
                text=[text],
                images=[image],
                padding=True,
                return_tensors="pt",
            )

        inputs = inputs.to(self.model.device)
        with torch.no_grad():
            generated_ids = self.model.generate(**inputs, max_new_tokens=512, do_sample=False)

        trimmed = [
            out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
        ]
        return self.processor.batch_decode(
            trimmed,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False,
        )[0]


# ── 6. Helper serializers ─────────────────────────────────────────────────────
def _pil_to_b64(img) -> str:
    from PIL import Image
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def _b64_to_pil(b64: str):
    from PIL import Image
    return Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB")


def _cleanup_cuda():
    try:
        import torch
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
    except Exception as exc:
        print(f"[cleanup] skipped: {exc}")


def _build_critic_prompt(body: dict) -> str:
    return f"""You are SmartSketch's forensic image critic. Inspect the generated face against the requested suspect profile.

Return ONLY a valid JSON object with this schema:
{{
  "decision": "accept" or "revise",
  "score": number from 0 to 100,
  "issues": ["short issue"],
  "matched_features": ["feature visible in image"],
  "missing_features": ["feature missing or weak"],
  "prompt_adjustment": "one concise SDXL edit/regeneration instruction, empty when accepted",
  "safety_flags": ["flag if any"],
  "reasoning_summary": "one concise audit-friendly sentence"
}}

Revise only when a visible mismatch can be corrected by a concrete prompt adjustment.

Suspect profile JSON:
{json.dumps(body.get("suspect_profile") or {}, ensure_ascii=False)}

Original prompt:
{body.get("prompt") or ""}

Route used: {body.get("route_used") or "unknown"}
Scores JSON: {json.dumps(body.get("scores") or {}, ensure_ascii=False)}
Metadata JSON: {json.dumps(body.get("metadata") or {}, ensure_ascii=False)}
"""


def _parse_critic_json(text: str) -> dict:
    fallback = {
        "decision": "accept",
        "score": None,
        "issues": ["critic_parse_error"],
        "matched_features": [],
        "missing_features": [],
        "prompt_adjustment": "",
        "safety_flags": [],
        "reasoning_summary": "Critic response could not be parsed; accepted by fallback.",
    }
    try:
        match = re.search(r"\{.*\}", text or "", re.DOTALL)
        data = json.loads(match.group(0) if match else text)
    except Exception:
        return fallback

    data.setdefault("decision", "accept")
    data["decision"] = "revise" if str(data["decision"]).lower() in {"revise", "retry", "reject"} else "accept"
    for key in ["issues", "matched_features", "missing_features", "safety_flags"]:
        if isinstance(data.get(key), str):
            data[key] = [data[key]]
        elif not isinstance(data.get(key), list):
            data[key] = []
    data.setdefault("prompt_adjustment", "")
    data.setdefault("reasoning_summary", "")
    return data


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

    @web_app.post("/critic")
    async def critic(request: Request):
        body = await request.json()
        result = ForensicCriticService().analyze.remote(body)
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
