"""
SmartSketch.AI - Memory-Efficient Sketch Converter
Reuses existing SDXL pipeline to save GPU memory
"""

import torch
import cv2
import numpy as np
from PIL import Image
from typing import Optional, Literal
from controlnet_aux import CannyDetector
from diffusers import ControlNetModel, StableDiffusionXLControlNetPipeline


class MemoryEfficientSketchConverter:
    """
    Converts photos to sketches while reusing existing SDXL pipeline
    """
    
    def __init__(
        self,
        base_pipeline=None,  # NEW: Reuse existing pipeline
        controlnet_model: str = "diffusers/controlnet-canny-sdxl-1.0",
        device: str = "cuda",
        enable_offload: bool = False
    ):
        """
        Initialize sketch converter
        
        Args:
            base_pipeline: Existing SDXL pipeline to reuse (saves memory!)
            controlnet_model: ControlNet model
            device: 'cuda' or 'cpu'
        """
        print("🎨 Loading Sketch Converter (memory-efficient)...")
        
        self.device = device
        self.base_pipeline = base_pipeline
        
        # Load Canny detector (lightweight)
        print("  - Loading Canny detector...")
        self.canny_detector = CannyDetector()
        
        # Load ControlNet (small model)
        print("  - Loading ControlNet...")
        self.controlnet = ControlNetModel.from_pretrained(
            controlnet_model,
            torch_dtype=torch.float16 if device == "cuda" else torch.float32
        ).to(device)
        
        # Create pipeline with ControlNet
        # This reuses the SDXL components from base_pipeline!
        print("  - Creating ControlNet pipeline...")
        if base_pipeline:
            # MEMORY SAVER: Reuse existing SDXL components
            self.pipe = StableDiffusionXLControlNetPipeline(
                vae=base_pipeline.vae,
                text_encoder=base_pipeline.text_encoder,
                text_encoder_2=base_pipeline.text_encoder_2,
                tokenizer=base_pipeline.tokenizer,
                tokenizer_2=base_pipeline.tokenizer_2,
                unet=base_pipeline.unet,
                scheduler=base_pipeline.scheduler,
                controlnet=self.controlnet
            )
        else:
            # Fallback: Load new pipeline (uses more memory)
            self.pipe = StableDiffusionXLControlNetPipeline.from_pretrained(
                "stabilityai/stable-diffusion-xl-base-1.0",
                controlnet=self.controlnet,
                torch_dtype=torch.float16 if device == "cuda" else torch.float32
            )
        
        if enable_offload and device == "cuda":
            print("  - Enabling Model CPU Offload & VAE Optimizations for Sketch Converter")
            self.pipe.enable_model_cpu_offload()
            self.pipe.enable_vae_slicing()
            self.pipe.enable_vae_tiling()
        else:
            self.pipe.to(device)
        
        print("✅ Sketch Converter ready (sharing SDXL components)!")
    
    def photo_to_sketch_simple(
        self,
        image: Image.Image,
        style: Literal["light", "medium", "dark"] = "medium"
    ) -> Image.Image:
        """
        Simple OpenCV sketch (CPU, fast, no GPU memory)
        """
        img_array = np.array(image)
        
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array
        
        inverted = 255 - gray
        
        blur_sizes = {"light": (11, 11), "medium": (21, 21), "dark": (31, 31)}
        blur_size = blur_sizes.get(style, (21, 21))
        blurred = cv2.GaussianBlur(inverted, blur_size, 0)
        
        inverted_blur = 255 - blurred
        sketch = cv2.divide(gray, inverted_blur, scale=256.0)
        sketch = cv2.normalize(sketch, None, 0, 255, cv2.NORM_MINMAX)
        
        return Image.fromarray(sketch)
    
    def photo_to_sketch_controlnet(
        self,
        image: Image.Image,
        style: Literal["pencil", "charcoal", "forensic"] = "forensic",
        detail_level: float = 0.8,
        num_inference_steps: int = 30,
        seed: Optional[int] = None
    ) -> Image.Image:
        """
        High-quality ControlNet sketch
        """
        if image.size != (512, 512):
            image = image.resize((512, 512), Image.Resampling.LANCZOS)
        
        print("🔍 Detecting edges...")
        canny_image = self.canny_detector(image)
        
        style_prompts = {
            "pencil": "pencil sketch, hand-drawn portrait, light shading, detailed lines, graphite drawing",
            "charcoal": "charcoal sketch, dark shading, dramatic portrait, heavy lines",
            "forensic": "forensic sketch, police sketch, professional portrait drawing, detailed facial features"
        }
        
        prompt = style_prompts.get(style, style_prompts["forensic"])
        
        negative_prompt = (
            "photo, photograph, photorealistic, realistic, color, colored, "
            "painting, anime, cartoon, low quality, blurry"
        )
        
        if seed is not None:
            generator = torch.Generator(device=self.device).manual_seed(seed)
        else:
            generator = None
        
        print(f"🎨 Converting to {style} sketch...")
        
        sketch = self.pipe(
            prompt=prompt,
            negative_prompt=negative_prompt,
            image=canny_image,
            num_inference_steps=num_inference_steps,
            controlnet_conditioning_scale=detail_level,
            guidance_scale=7.5,
            generator=generator
        ).images[0]
        
        print("✅ Sketch generated!")
        return sketch
    
    def convert(
        self,
        image: Image.Image,
        method: Literal["simple", "controlnet"] = "controlnet",
        **kwargs
    ) -> Image.Image:
        """Main conversion method"""
        if method == "simple":
            return self.photo_to_sketch_simple(image, **kwargs)
        else:
            return self.photo_to_sketch_controlnet(image, **kwargs)


# Convenience function
def convert_to_sketch(
    image: Image.Image,
    method: str = "controlnet",
    style: str = "forensic",
    converter: Optional[MemoryEfficientSketchConverter] = None,
    **kwargs
) -> Image.Image:
    """Quick sketch conversion"""
    if converter is None:
        converter = MemoryEfficientSketchConverter()
    
    return converter.convert(image, method=method, style=style, **kwargs)