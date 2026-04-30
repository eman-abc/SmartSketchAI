"""
api/ml_service.py  —  Django-side ML Service

Architecture
============
ALL heavy GPU work (SDXL, Qwen, CLIP, FaceNet, ControlNet, inpainting)
runs exclusively on the Colab notebook.

Django (Render) is CPU-only and acts as an API gateway:
  - generate / edit views  → HTTP POST to Colab Flask (/generate, /edit)
  - agent_chat view        → LangGraph agent whose _artist_node calls Colab

Nothing in this file loads torch models.  `get_pipeline()` is intentionally
disabled unless USE_LOCAL_ML=True (for local GPU development only).
"""

from django.conf import settings


class MLService:
    """
    Singleton factory for the agent (and optionally the local pipeline).

    On Render (production):
        get_pipeline() raises RuntimeError   – no heavy models loaded
        get_agent()    returns a lightweight agent wired to the Colab URL

    Locally with a GPU:
        Set USE_LOCAL_ML=True in .env to enable the full local pipeline.
    """

    _pipeline = None
    _agent    = None

    # ------------------------------------------------------------------
    # Pipeline  (local GPU only)
    # ------------------------------------------------------------------

    @classmethod
    def get_pipeline(cls):
        """
        Returns the local SmartSketchPipeline.
        Raises RuntimeError when USE_LOCAL_ML=False (default on Render).
        Heavy imports (torch, diffusers, …) only happen inside this method.
        """
        ml_config = getattr(settings, "ML_CONFIG", {})
        if not ml_config.get("USE_LOCAL_ML", False):
            raise RuntimeError(
                "Local ML engine is disabled (USE_LOCAL_ML=False). "
                "All inference runs on the Colab notebook."
            )

        if cls._pipeline is None:
            import os
            # Defer heavy imports so they never run unless we actually need them
            import torch
            from ml_engine.pipeline import SmartSketchPipeline

            device   = ml_config.get("DEVICE", "cuda" if torch.cuda.is_available() else "cpu")
            lora_path = ml_config.get("LORA_PATH")
            if lora_path and not os.path.exists(lora_path):
                print(f"[MLService] LoRA weights not found at {lora_path} — loading without LoRA.")
                lora_path = None

            print("[MLService] Loading local SmartSketch pipeline …")
            cls._pipeline = SmartSketchPipeline.from_pretrained(
                lora_path=lora_path,
                validator_model=ml_config.get("VALIDATOR_MODEL", "Qwen/Qwen2.5-3B-Instruct"),
                sdxl_model=ml_config.get("SDXL_MODEL", "stabilityai/stable-diffusion-xl-base-1.0"),
                lora_strength=ml_config.get("LORA_STRENGTH", 0.3),
                device=device,
                enable_sketch=ml_config.get("ENABLE_SKETCH", True),
                enable_editing=ml_config.get("ENABLE_EDITING", True),
                enable_inpainting=ml_config.get("ENABLE_INPAINTING", True),
                enable_offload=ml_config.get("LOW_VRAM_MODE", False),
            )
            print("[MLService] Local pipeline ready.")

        return cls._pipeline

    # ------------------------------------------------------------------
    # Agent  (always lightweight — routes inference to Colab)
    # ------------------------------------------------------------------

    @classmethod
    def get_agent(cls):
        """
        Returns the stateful LangGraph agent.

        In remote mode (USE_LOCAL_ML=False, default on Render):
          - No heavy models are loaded.
          - _artist_node calls the Colab Flask server via HTTP.
          - VerificationNode skips CLIP scoring (scorer=None → pass-through).

        In local GPU mode (USE_LOCAL_ML=True):
          - The full local pipeline is loaded and used directly.
        """
        if cls._agent is not None:
            return cls._agent

        print("[MLService] Initialising SmartSketch Agent …")

        ml_config  = getattr(settings, "ML_CONFIG", {})
        use_local  = ml_config.get("USE_LOCAL_ML", False)
        remote_url = ml_config.get("REMOTE_ML_URL", "")

        # Only load local pipeline when explicitly enabled (local GPU dev)
        local_pipeline = None
        if use_local:
            try:
                local_pipeline = cls.get_pipeline()
            except Exception as e:
                print(f"[MLService] Local pipeline unavailable: {e}")

        # Lightweight import — no torch/diffusers at module level
        from ml_engine.agent import SmartSketchAgent

        # Set up Gemini LLM if API key is available
        llm = None
        gemini_api_key = getattr(settings, "GEMINI_API_KEY", None) or ml_config.get("GEMINI_API_KEY")
        if not gemini_api_key:
            import os
            gemini_api_key = os.environ.get("GEMINI_API_KEY")
            
        if gemini_api_key:
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
                print("[MLService] Initialising Gemini 1.5 Flash for Semantic Routing...")
                llm = ChatGoogleGenerativeAI(
                    model="gemini-1.5-flash",
                    google_api_key=gemini_api_key,
                    temperature=0.0
                )
            except ImportError:
                print("[MLService] langchain-google-genai not installed. Falling back to mock LLM routing.")
            except Exception as e:
                print(f"[MLService] Failed to load Gemini LLM: {e}. Falling back to mock LLM routing.")

        cls._agent = SmartSketchAgent(
            llm=llm,
            pipeline=local_pipeline,
            remote_url=remote_url or None,
        )

        mode = "local GPU" if local_pipeline else f"remote Colab ({remote_url or 'URL not set!'})"
        print(f"[MLService] Agent ready in {mode} mode.")
        return cls._agent
