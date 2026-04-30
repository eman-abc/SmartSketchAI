"""
SmartSketch.AI - Generator Module
Generates faces using SDXL + LoRA
"""

import torch
from diffusers import StableDiffusionXLPipeline
from PIL import Image
from typing import Optional


class FaceGenerator:
    """
    Generates faces using SDXL + fine-tuned LoRA
    
    Features:
    - Photorealistic face generation
    - LoRA fine-tuning support
    - Reproducible outputs (seed-based)
    """
    
    def __init__(
        self,
        model_path: str = "stabilityai/stable-diffusion-xl-base-1.0",
        lora_path: Optional[str] = None,
        lora_strength: float = 0.3,
        device: str = "cuda",
        enable_offload: bool = False
    ):
        """
        Initialize the generator
        
        Args:
            model_path: Path to SDXL base model (local or HuggingFace)
            lora_path: Path to LoRA weights (.safetensors file)
            lora_strength: LoRA influence (0.0-1.0, default 0.3 for realism)
            device: 'cuda' or 'cpu'
        """
        print(f"📥 Loading SDXL from {model_path}...")
        
        self.device = device
        self.lora_strength = lora_strength
        
        # Load base SDXL
        self.pipe = StableDiffusionXLPipeline.from_pretrained(
            model_path,
            torch_dtype=torch.float16 if device == "cuda" else torch.float32,
            variant="fp16" if device == "cuda" else None,
            use_safetensors=True
        )
        
        # Load LoRA if provided
        if lora_path:
            print(f"📥 Loading LoRA from {lora_path}...")
            self.pipe.load_lora_weights(lora_path, adapter_name="forensic")
            self.pipe.set_adapters("forensic", adapter_weights=[lora_strength])
            print(f"✅ LoRA loaded (strength: {lora_strength})")
            
        # Load IP-Adapter for face consistency
        print("📥 Loading IP-Adapter FaceID...")
        try:
            self.pipe.load_ip_adapter("h94/IP-Adapter", subfolder="sdxl_models", weight_name="ip-adapter_sdxl.bin")
            self.pipe.set_ip_adapter_scale(0.6)
            print("✅ IP-Adapter loaded successfully")
        except Exception as e:
            print(f"⚠️ IP-Adapter failed to load: {e}")
        
        # Move to device
        if enable_offload and device == "cuda":
            print("  - Enabling Model CPU Offload & VAE Optimizations (Balanced Mode)")
            self.pipe.enable_model_cpu_offload()
            self.pipe.enable_vae_slicing()
            self.pipe.enable_vae_tiling()
        else:
            self.pipe.to(device)
        
        print(f"✅ Generator ready on {device}")
    
    def generate_face(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        seed: Optional[int] = None,
        num_inference_steps: int = 30,
        guidance_scale: float = 7.5,
        width: int = 1024,
        height: int = 1024,
        reference_image: Optional[Image.Image] = None
    ) -> Image.Image:
        """
        Generate a face from text description
        
        Args:
            prompt: Text description (preferably enhanced by validator)
            negative_prompt: What to avoid (optional)
            seed: Random seed for reproducibility
            num_inference_steps: Generation quality (20-50, higher=better)
            guidance_scale: Prompt adherence (7-8 recommended)
            width: Image width in pixels
            height: Image height in pixels
        
        Returns:
            PIL Image
        """
        # Default negative prompt for forensic realism
        if negative_prompt is None:
            negative_prompt = (
                "anime, cartoon, 3d render, stylized, unrealistic, "
                "colorful, illustration, painting, fantasy, video game, "
                "neon, oversaturated"
            )
        
        # Enhance prompt for forensic style
        full_prompt = f"professional forensic photograph, {prompt}, realistic, photorealistic, natural skin tones, detailed facial features"
        
        # Set up generator for reproducibility
        if seed is not None:
            generator = torch.Generator(device=self.device).manual_seed(seed)
        else:
            generator = None
        
        # Generate
        kwargs = {}
        if reference_image is not None:
            kwargs["ip_adapter_image"] = reference_image
            
        image = self.pipe(
            prompt=full_prompt,
            negative_prompt=negative_prompt,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            generator=generator,
            width=width,
            height=height,
            **kwargs
        ).images[0]
        
        return image
    
    def set_lora_strength(self, strength: float):
        """
        Adjust LoRA influence
        
        Args:
            strength: New strength value (0.0-1.0)
        """
        self.lora_strength = strength
        if hasattr(self.pipe, 'set_adapters'):
            self.pipe.set_adapters("forensic", adapter_weights=[strength])
            print(f"✅ LoRA strength updated to {strength}")


# Convenience function for quick usage
def generate_face(
    prompt: str,
    seed: Optional[int] = None,
    generator: Optional[FaceGenerator] = None,
    **kwargs
) -> Image.Image:
    """
    Quick generation function
    
    Args:
        prompt: Text description
        seed: Random seed for reproducibility
        generator: Optional pre-initialized generator (for performance)
        **kwargs: Additional generation parameters
    
    Returns:
        PIL Image
    """
    if generator is None:
        generator = FaceGenerator()
    
    return generator.generate_face(prompt, seed=seed, **kwargs)
