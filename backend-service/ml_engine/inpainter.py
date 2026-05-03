"""
SmartSketch.AI - Face Inpainter
Precision semantic editing using SDXL Inpainting with identity preservation.
"""
import os
import random
from datetime import datetime

import torch
from diffusers import StableDiffusionXLInpaintPipeline
from PIL import Image
from typing import Optional, Dict

from .masker import FaceMasker

# ---------------------------------------------------------------------------
# IMPORTANT: The inpainting UNet has 9 input channels (4 latent + 4 masked
# latent + 1 mask), which is DIFFERENT from the base SDXL UNet (4 channels).
# We MUST load the dedicated inpainting checkpoint; we cannot reuse the
# generator's UNet components.
# ---------------------------------------------------------------------------
INPAINT_MODEL = "diffusers/stable-diffusion-xl-1.0-inpainting-0.1"


def _identity_preserved_min() -> float:
    try:
        v = float(os.environ.get("SMARTSKETCH_IDENTITY_PRESERVED_THRESHOLD", "0.55").strip())
        return v if v == v else 0.55
    except (TypeError, ValueError):
        return 0.55


class FaceInpainter:
    """
    Precision semantic editing using SDXL Inpainting.

    - Generates a MediaPipe facial-landmark mask for the target region.
    - Runs SDXL inpainting so only the masked pixels are changed.
    - Measures identity preservation (cosine similarity via FaceNet, SSIM fallback).
    """

    def __init__(
        self,
        base_pipeline=None,   # kept for API compatibility, not used for UNet
        device: str = "cuda",
        enable_offload: bool = False,
    ):
        print("[Inpainter] Loading Face Inpainter …")
        self.device = device
        self.masker = FaceMasker()

        # Load dedicated inpainting model (9-channel UNet – cannot reuse base UNet)
        print(f"  - Loading SDXL inpainting model: {INPAINT_MODEL}")
        self.pipe = StableDiffusionXLInpaintPipeline.from_pretrained(
            INPAINT_MODEL,
            torch_dtype=torch.float16 if device == "cuda" else torch.float32,
            use_safetensors=True,
        )

        # Load IP-Adapter for face consistency in inpainting
        print("📥 Loading IP-Adapter FaceID for inpainting...")
        try:
            self.pipe.load_ip_adapter("h94/IP-Adapter", subfolder="sdxl_models", weight_name="ip-adapter_sdxl.bin")
            self.pipe.set_ip_adapter_scale(0.6)
            print("✅ IP-Adapter loaded successfully")
        except Exception as e:
            print(f"⚠️ IP-Adapter failed to load: {e}")

        if enable_offload and device == "cuda":
            print("  - Enabling Model CPU Offload & VAE optimisations for Inpainter")
            self.pipe.enable_model_cpu_offload()
            self.pipe.enable_vae_slicing()
            self.pipe.enable_vae_tiling()
        else:
            self.pipe.to(device)

        # Optional: FaceNet for identity preservation scoring
        try:
            from facenet_pytorch import MTCNN, InceptionResnetV1
            self._detector = MTCNN(device=device, post_process=False)
            self._identity_model = InceptionResnetV1(pretrained="vggface2").eval().to(device)
            self._has_facenet = True
            print("  - FaceNet identity model loaded")
        except ImportError:
            self._detector = None
            self._identity_model = None
            self._has_facenet = False
            print("  - FaceNet not available; identity scored via SSIM fallback")

        print("✅ Face Inpainter ready!")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def inpaint_edit(
        self,
        image: Image.Image,
        prompt: str,
        target_region: Optional[str] = None,
        strength: float = 0.75,
        num_inference_steps: int = 30,
        seed: Optional[int] = None,
        negative_prompt: Optional[str] = None,
    ) -> Dict:
        """
        Edit a specific region of the face while preserving identity.

        Returns a dict with keys:
            success, edited_image, mask, target_region,
            identity_score, identity_preserved, edit_id, metadata
        """
        edit_id = f"inpaint_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{random.randint(1000, 9999)}"
        timestamp = datetime.now().isoformat()

        # Auto-detect region from prompt text if caller didn't specify one
        if not target_region:
            target_region = self.masker.detect_region_from_prompt(prompt)

        print(f"\n[Inpainter] edit_id={edit_id}  region={target_region}  prompt=\"{prompt}\"")

        # Normalise image to 1024×1024 (SDXL native resolution)
        if image.size != (1024, 1024):
            image = image.resize((1024, 1024), Image.Resampling.LANCZOS)

        # Generate semantic mask
        mask = self.masker.create_mask(image, target_region)
        if mask is None:
            return {
                "success": False,
                "error": f"Could not generate mask for region: {target_region}",
                "edit_id": edit_id,
            }

        # Reproducibility
        generator = (
            torch.Generator(device=self.device).manual_seed(seed)
            if seed is not None
            else None
        )

        full_prompt = (
            f"professional forensic photograph, {prompt}, "
            "realistic, photorealistic, natural skin tones, detailed facial features, high quality"
        )
        base_negative = (
            "low quality, blurry, distorted, deformed, disfigured, "
            "anime, cartoon, 3d render, painting, duplicate"
        )
        if negative_prompt:
            negative_prompt = f"{base_negative}, {negative_prompt}"
        else:
            negative_prompt = base_negative


        try:
            print(f"🎨 [Inpainter] Running inpainting on region: {target_region} …")
            kwargs = {}
            if getattr(self.pipe, 'image_encoder', None) is not None:
                kwargs["ip_adapter_image"] = image

            result_image = self.pipe(
                prompt=full_prompt,
                negative_prompt=negative_prompt,
                image=image,
                mask_image=mask,
                strength=strength,
                num_inference_steps=num_inference_steps,
                generator=generator,
                num_images_per_prompt=1,
                **kwargs
            ).images[0]

            # Measure identity preservation
            print("👤 [Inpainter] Computing identity preservation …")
            identity_score = self._compute_identity(image, result_image)
            identity_preserved = identity_score >= _identity_preserved_min()
            print(f"   Identity score: {identity_score:.1%}  preserved={identity_preserved}")

            return {
                "success": True,
                "edited_image": result_image,
                "mask": mask,
                "target_region": target_region,
                "identity_score": float(identity_score),
                "identity_preserved": identity_preserved,
                "edit_id": edit_id,
                "metadata": {
                    "timestamp": timestamp,
                    "edit_id": edit_id,
                    "target_region": target_region,
                    "prompt": prompt,
                    "strength": strength,
                    "num_inference_steps": num_inference_steps,
                    "seed": seed,
                    "identity_score": float(identity_score),
                    "identity_preserved": identity_preserved,
                },
            }

        except Exception as e:
            print(f"❌ [Inpainter] Inpainting failed: {e}")
            return {"success": False, "error": f"Inpaint failed: {str(e)}", "edit_id": edit_id}

    # ------------------------------------------------------------------
    # Identity scoring helpers
    # ------------------------------------------------------------------

    def _compute_identity(
        self, original: Image.Image, edited: Image.Image
    ) -> float:
        """Cosine similarity of FaceNet embeddings; falls back to SSIM."""
        if self._has_facenet:
            return self._facenet_score(original, edited)
        return self._ssim_score(original, edited)

    def _facenet_score(self, orig: Image.Image, edit: Image.Image) -> float:
        import torch.nn.functional as F

        try:
            orig_face = self._detector(orig)
            edit_face = self._detector(edit)

            if orig_face is None or edit_face is None:
                print("[Inpainter] Face not detected – falling back to SSIM")
                return self._ssim_score(orig, edit)

            with torch.no_grad():
                emb_orig = self._identity_model(orig_face.unsqueeze(0).to(self.device))
                emb_edit = self._identity_model(edit_face.unsqueeze(0).to(self.device))
                sim = F.cosine_similarity(emb_orig, emb_edit).item()

            return max(0.0, float(sim))

        except Exception as e:
            print(f"[Inpainter] FaceNet error: {e} – falling back to SSIM")
            return self._ssim_score(orig, edit)

    def _ssim_score(self, orig: Image.Image, edit: Image.Image) -> float:
        try:
            import cv2
            import numpy as np
            from skimage.metrics import structural_similarity as ssim

            orig_gray = np.array(orig.convert("L"))
            edit_gray = np.array(edit.convert("L"))
            if orig_gray.shape != edit_gray.shape:
                edit_gray = cv2.resize(edit_gray, (orig_gray.shape[1], orig_gray.shape[0]))
            return float(ssim(orig_gray, edit_gray))
        except Exception:
            return 0.5  # neutral fallback
