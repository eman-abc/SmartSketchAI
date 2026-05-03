# ============================================
# CELL 1: Create editor.py
# ============================================

import os
import random
from datetime import datetime
from typing import Dict, Optional

import torch
from controlnet_aux import CannyDetector
from diffusers import StableDiffusionXLControlNetImg2ImgPipeline, ControlNetModel
from PIL import Image


def _env_float(name: str, default: float) -> float:
    try:
        v = float(os.environ.get(name, "").strip())
        if v != v:  # NaN
            return default
        return v
    except (TypeError, ValueError):
        return default


# Looser defaults: easier "identity_preserved", softer Canny lock, weaker IP-Adapter identity pull
_IDENTITY_PRESERVED_MIN = _env_float("SMARTSKETCH_IDENTITY_PRESERVED_THRESHOLD", 0.55)
_CONTROLNET_CONDITIONING = _env_float("SMARTSKETCH_CONTROLNET_CONDITIONING_SCALE", 0.65)
_EDIT_IP_ADAPTER_DEFAULT = _env_float("SMARTSKETCH_EDIT_IP_ADAPTER_SCALE", 0.5)

try:
    from facenet_pytorch import MTCNN, InceptionResnetV1
    HAS_FACENET = True
except ImportError:
    HAS_FACENET = False


class FaceEditor:
    """
    Edit faces using SDXL img2img
    
    Features:
    - Modify facial features (glasses, hair, beard, etc.)
    - Preserve identity
    - Iterative refinement
    """
    
    def __init__(
        self,
        base_pipeline=None,
        device: str = "cuda",
        enable_offload: bool = False
    ):
        """
        Initialize face editor
        
        Args:
            base_pipeline: Existing SDXL pipeline to reuse (saves memory!)
            device: cuda or cpu
        """
        print("[Editor] Loading Face Editor...")
        
        self.device = device
        
        # Load ControlNet for geometric locking (NEW)
        print("  - Loading Canny ControlNet for geometric locking...")
        self.controlnet = ControlNetModel.from_pretrained(
            "diffusers/controlnet-canny-sdxl-1.0",
            torch_dtype=torch.float16 if device == "cuda" else torch.float32
        ).to(device)
        
        self.canny_detector = CannyDetector()

        # Reuse existing SDXL components (saves memory!)
        if base_pipeline:
            print("  - Reusing SDXL components from generator...")
            self.pipe = StableDiffusionXLControlNetImg2ImgPipeline(
                vae=base_pipeline.vae,
                text_encoder=base_pipeline.text_encoder,
                text_encoder_2=base_pipeline.text_encoder_2,
                tokenizer=base_pipeline.tokenizer,
                tokenizer_2=base_pipeline.tokenizer_2,
                unet=base_pipeline.unet,
                scheduler=base_pipeline.scheduler,
                controlnet=self.controlnet,
                image_encoder=getattr(base_pipeline, 'image_encoder', None),
                feature_extractor=getattr(base_pipeline, 'feature_extractor', None)
            )
        else:
            print("  - Loading new SDXL ControlNet Img2Img pipeline...")
            self.pipe = StableDiffusionXLControlNetImg2ImgPipeline.from_pretrained(
                "stabilityai/stable-diffusion-xl-base-1.0",
                controlnet=self.controlnet,
                torch_dtype=torch.float16 if device == "cuda" else torch.float32
            )
        
        if enable_offload and device == "cuda":
            print("  - Enabling Model CPU Offload & VAE Optimizations for Editor")
            self.pipe.enable_model_cpu_offload()
            self.pipe.enable_vae_slicing()
            self.pipe.enable_vae_tiling()
        else:
            self.pipe.to(device)
        
        # Edit type presets — slightly higher strength so edits read more clearly (looser / less timid)
        self.edit_presets = {
            'glasses': {'strength': 0.64, 'guidance': 7.5},
            'beard': {'strength': 0.72, 'guidance': 7.5},
            'hair': {'strength': 0.68, 'guidance': 7.0},
            'hair_color': {'strength': 0.58, 'guidance': 7.0},
            'age': {'strength': 0.76, 'guidance': 8.0},
            'expression': {'strength': 0.54, 'guidance': 7.0},
            'accessories': {'strength': 0.64, 'guidance': 7.5},
            'default': {'strength': 0.72, 'guidance': 7.5},
        }
        
        # Load Identity Models (NEW)
        if HAS_FACENET:
            print("[Identity] Loading Face Recognition models (MTCNN + InceptionResnetV1)...")
            self.detector = MTCNN(device=device, post_process=False)
            self.identity_model = InceptionResnetV1(pretrained='vggface2').eval().to(device)
        else:
            print("[Warning] facenet-pytorch not found. Falling back to SSIM for identity scoring.")
            self.detector = None
            self.identity_model = None

        print("[Editor] Face Editor ready!")
    
    def detect_edit_type(self, edit_prompt: str) -> str:
        """Auto-detect edit type from prompt"""
        prompt_lower = edit_prompt.lower()
        
        if any(word in prompt_lower for word in ['glasses', 'spectacles', 'eyeglasses']):
            return 'glasses'
        elif any(word in prompt_lower for word in ['beard', 'mustache', 'facial hair']):
            return 'beard'
        elif 'color' in prompt_lower and 'hair' in prompt_lower:
            return 'hair_color'
        elif any(word in prompt_lower for word in ['hair', 'hairstyle', 'haircut']):
            return 'hair'
        elif any(word in prompt_lower for word in ['older', 'younger', 'age']):
            return 'age'
        elif any(word in prompt_lower for word in ['smile', 'expression', 'frown', 'serious']):
            return 'expression'
        elif any(word in prompt_lower for word in ['hat', 'cap', 'jewelry', 'earring']):
            return 'accessories'
        else:
            return 'default'
    
    def compute_identity_preservation(
        self,
        original_image: Image.Image,
        edited_image: Image.Image
    ) -> float:
        """
        Measure how well identity was preserved using Face Embeddings (Cosine Similarity)
        
        Returns:
            Score 0-1 (higher = better preservation)
        """
        if not HAS_FACENET or self.identity_model is None:
            return self._compute_ssim_fallback(original_image, edited_image)

        try:
            import torch.nn.functional as F
            
            # 1. Detect and crop faces
            orig_face = self.detector(original_image)
            edit_face = self.detector(edited_image)

            if orig_face is None or edit_face is None:
                print("[Warning] Could not detect face in one of the images. Falling back to SSIM.")
                return self._compute_ssim_fallback(original_image, edited_image)

            # 2. Get embeddings
            with torch.no_grad():
                # self.detector returns tensor (3, 160, 160)
                # We need (1, 3, 160, 160)
                orig_embedding = self.identity_model(orig_face.unsqueeze(0).to(self.device))
                edit_embedding = self.identity_model(edit_face.unsqueeze(0).to(self.device))

                # 3. Compute Cosine Similarity
                similarity = F.cosine_similarity(orig_embedding, edit_embedding).item()
            
            # Normalize: Cosine similarity for embeddings is typically 0.6+ for same person
            # We'll keep it as is, or slightly scale it if needed. 
            # 1.0 is identical, <0.5 is usually different person.
            return max(0.0, float(similarity))

        except Exception as e:
            print(f"⚠️  Embedding scoring failed: {e}. Falling back to SSIM.")
            return self._compute_ssim_fallback(original_image, edited_image)

    def _compute_ssim_fallback(self, original_image: Image.Image, edited_image: Image.Image) -> float:
        """Fallback SSIM scoring if facenet is unavailable"""
        try:
            import cv2
            import numpy as np
            from skimage.metrics import structural_similarity as ssim
            
            orig_gray = np.array(original_image.convert('L'))
            edit_gray = np.array(edited_image.convert('L'))
            
            if orig_gray.shape != edit_gray.shape:
                edit_gray = cv2.resize(edit_gray, (orig_gray.shape[1], orig_gray.shape[0]))
            
            return float(ssim(orig_gray, edit_gray))
        except:
            return 0.5 # Neutral fallback
    def edit_face(
        self,
        original_image: Image.Image,
        edit_prompt: str,
        strength: Optional[float] = None,
        guidance_scale: Optional[float] = None,
        num_inference_steps: int = 30,
        seed: Optional[int] = None,
        negative_prompt: Optional[str] = None,
        ip_adapter_scale: Optional[float] = None
    ) -> Dict:
        """
        Edit a face
        
        Args:
            original_image: PIL Image of original face
            edit_prompt: What to change (e.g., "add round glasses")
            strength: How much to change (0.0-1.0, auto if None)
            guidance_scale: Prompt adherence (auto if None)
            num_inference_steps: Quality (20-50, default 30)
            seed: Random seed for reproducibility
            negative_prompt: What to avoid (optional)
        
        Returns:
            Dictionary with:
            - success: bool
            - edit_id: str
            - original_image: PIL Image
            - edited_image: PIL Image
            - identity_score: float (0-1)
            - metadata: dict
        """
        
        # Generate edit ID
        edit_id = f"edit_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{random.randint(1000, 9999)}"
        timestamp = datetime.now().isoformat()
        
        print(f"\n{'='*60}")
        print(f"✏️  EDITING FACE")
        print(f"{'='*60}")
        print(f"🆔 Edit ID: {edit_id}")
        print(f"📝 Edit: {edit_prompt}")
        
        # Auto-detect edit type
        edit_type = self.detect_edit_type(edit_prompt)
        preset = self.edit_presets.get(edit_type, self.edit_presets['default'])
        
        # Use preset or provided values
        if strength is None:
            strength = preset['strength']
        if guidance_scale is None:
            guidance_scale = preset['guidance']
        
        print(f"🎯 Edit Type: {edit_type}")
        print(f"⚙️  Strength: {strength:.2f} (0=no change, 1=full change)")
        print(f"⚙️  Guidance: {guidance_scale}")
        
        # Resize if needed
        if original_image.size != (512, 512):
            print("📐 Resizing to 512x512...")
            original_image = original_image.resize((512, 512), Image.Resampling.LANCZOS)
        
        # Build full prompt
        full_prompt = f"professional forensic photograph, {edit_prompt}, realistic, photorealistic, natural skin tones, detailed facial features, high quality"
        
        base_negative = (
            "low quality, blurry, distorted, deformed, disfigured, "
            "bad anatomy, extra limbs, poorly drawn face, mutation, "
            "anime, cartoon, 3d render, duplicate, multiple people"
        )
        if negative_prompt:
            negative_prompt = f"{base_negative}, {negative_prompt}"
        else:
            negative_prompt = base_negative

        
        # Set up generator for reproducibility
        if seed is not None:
            generator = torch.Generator(device=self.device).manual_seed(seed)
        else:
            generator = None
        
        print(f"🎨 Applying precision edit with ControlNet lock...")
        
        try:
            # 1. Generate Canny edge map
            canny_image = self.canny_detector(original_image)

            # 2. Generate edited image (num_images_per_prompt=1 ensures single output)
            kwargs = {}
            if getattr(self.pipe, 'image_encoder', None) is not None:
                kwargs["ip_adapter_image"] = original_image
                # Set IP-Adapter scale if provided or use default 0.6
                current_scale = (
                    ip_adapter_scale
                    if ip_adapter_scale is not None
                    else _EDIT_IP_ADAPTER_DEFAULT
                )
                self.pipe.set_ip_adapter_scale(current_scale)
                print(f"🔗 IP-Adapter scale set to {current_scale}")
                
            edited_image = self.pipe(
                prompt=full_prompt,
                negative_prompt=negative_prompt,
                image=original_image,
                control_image=canny_image,
                strength=strength,
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale,
                controlnet_conditioning_scale=_CONTROLNET_CONDITIONING,
                num_images_per_prompt=1,             # Guarantee single output image
                generator=generator,
                **kwargs
            ).images[0]
            
            print("✅ Edit complete!")
            
            # Compute identity preservation
            print("👤 Computing identity preservation...")
            identity_score = self.compute_identity_preservation(
                original_image,
                edited_image
            )
            print(f"   Identity preserved: {identity_score:.1%}")
            
            identity_preserved = identity_score >= _IDENTITY_PRESERVED_MIN
            
            return {
                'success': True,
                'edit_id': edit_id,
                'original_image': original_image,
                'edited_image': edited_image,
                'identity_score': identity_score,
                'identity_preserved': identity_preserved,
                'edit_prompt': edit_prompt,
                'metadata': {
                    'timestamp': timestamp,
                    'edit_id': edit_id,
                    'edit_prompt': edit_prompt,
                    'edit_type': edit_type,
                    'strength': strength,
                    'guidance_scale': guidance_scale,
                    'num_inference_steps': num_inference_steps,
                    'seed': seed,
                    'identity_score': identity_score,
                    'identity_preserved': identity_preserved
                }
            }
            
        except Exception as e:
            print(f"❌ Edit failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'edit_id': edit_id,
                'timestamp': timestamp
            }
    
    def batch_edit(
        self,
        original_image: Image.Image,
        edit_prompts: list,
        **kwargs
    ) -> list:
        """
        Apply multiple edits to the same image
        
        Args:
            original_image: PIL Image
            edit_prompts: List of edit descriptions
            **kwargs: Additional parameters for edit_face
        
        Returns:
            List of edit result dictionaries
        """
        print(f"\\n{'='*60}")
        print(f"🔄 BATCH EDITING: {len(edit_prompts)} edits")
        print(f"{'='*60}")
        
        results = []
        
        for i, prompt in enumerate(edit_prompts, 1):
            print(f"\\n[{i}/{len(edit_prompts)}] {prompt}")
            
            result = self.edit_face(
                original_image=original_image,
                edit_prompt=prompt,
                **kwargs
            )
            results.append(result)
        
        successful = sum(1 for r in results if r['success'])
        print(f"\\n{'='*60}")
        print(f"✅ Batch complete: {successful}/{len(edit_prompts)} successful")
        print(f"{'='*60}")
        
        return results

    def age_edit(
        self,
        original_image: Image.Image,
        years: int,
        enhanced_prompt: Optional[str] = None,
        **kwargs
    ) -> Dict:
        """
        Perform age progression or regression
        
        Args:
            original_image: PIL Image
            years: Number of years to age (positive) or de-age (negative)
            enhanced_prompt: Optional pre-enhanced prompt from LLM
            **kwargs: Overrides for edit_face
        """
        age_direction = "older" if years > 0 else "younger"
        abs_years = abs(years)
        
        # Build a specialized forensic aging prompt
        if enhanced_prompt:
            edit_prompt = enhanced_prompt
        else:
            if years > 0:
                if abs_years < 10:
                    keywords = "subtle age progression, fine lines around eyes"
                elif abs_years < 25:
                    keywords = "middle-aged, deepening facial lines, sun-damaged skin texture"
                else:
                    keywords = "elderly appearance, deep wrinkles, sagging skin, grey hair, age spots"
            else:
                keywords = "younger appearance, smooth skin, youthful facial structure, vibrant complexion"
            
            edit_prompt = f"same person, {abs_years} years {age_direction}, {keywords}"

        print(f"[AgeEdit] Direction: {age_direction} ({abs_years} years)")
        
        # Apply Reformed Plan: Lower IP-Adapter scale to allow aging
        # but keep ControlNet high (0.8) to lock bone structure.
        # Defaults for aging:
        strength = kwargs.pop('strength', 0.75)
        ip_scale = kwargs.pop('ip_adapter_scale', 0.35) # REFORMED: Low scale for aging
        
        return self.edit_face(
            original_image=original_image,
            edit_prompt=edit_prompt,
            strength=strength,
            ip_adapter_scale=ip_scale,
            **kwargs
        )


# Convenience function
def edit_face(
    original_image: Image.Image,
    edit_prompt: str,
    editor: Optional[FaceEditor] = None,
    **kwargs
) -> Dict:
    """
    Quick edit function
    
    Args:
        original_image: PIL Image
        edit_prompt: What to change
        editor: Optional pre-initialized editor
        **kwargs: Additional parameters
    
    Returns:
        Edit result dictionary
    """
    if editor is None:
        editor = FaceEditor()
    
    return editor.edit_face(original_image, edit_prompt, **kwargs)

