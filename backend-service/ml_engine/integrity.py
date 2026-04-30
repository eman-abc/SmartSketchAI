import hashlib
import numpy as np
from PIL import Image
import os
from typing import Tuple
from imwatermark import WatermarkEncoder, WatermarkDecoder

class ForensicSigner:
    """
    Handles image integrity via invisible watermarking and cryptographic hashing
    """
    def __init__(self, watermark_text: str = "SMARTSKETCH_AI"):
        self.watermark_text = watermark_text
        self.encoder = WatermarkEncoder()
        self.encoder.set_watermark('bytes', watermark_text.encode('utf-8'))
        
        # Use 'dwtDct' method - it's robust and does not require a GPU/Neural Net
        self.method = 'dwtDct'

    def sign_image(self, image: Image.Image) -> Image.Image:
        """
        Embed an invisible watermark into the image
        """
        try:
            # Convert PIL to numpy (RGB)
            img_np = np.array(image)
            
            # Encode watermark
            print(f"[Integrity] Embedding invisible watermark: {self.watermark_text}")
            signed_img_np = self.encoder.encode(img_np, self.method)
            
            # Convert back to PIL
            return Image.fromarray(signed_img_np.astype(np.uint8))
        except Exception as e:
            print(f"[!] Watermarking failed: {e}. Returning original image.")
            return image

    def calculate_hash(self, image: Image.Image) -> str:
        """
        Generate a SHA-256 cryptographic hash of the image
        """
        # We hash the pixel data to ensure it's independent of file format metadata
        img_bytes = image.tobytes()
        sha256_hash = hashlib.sha256(img_bytes).hexdigest()
        print(f"[Integrity] Forensic Hash: {sha256_hash}")
        return sha256_hash

    def verify_watermark(self, image: Image.Image) -> bool:
        """
        Try to decode the watermark to verify authenticity
        """
        try:
            img_np = np.array(image)
            decoder = WatermarkDecoder('bytes', len(self.watermark_text.encode('utf-8')) * 8)
            decoded = decoder.decode(img_np, self.method)
            return decoded.decode('utf-8') == self.watermark_text
        except:
            return False

class ForensicSafetyChecker:
    """
    Wrapper for SDXL Safety Checker with offloading
    """
    def __init__(self, device="cuda"):
        self.device = device
        self.safety_checker = None
        self.feature_extractor = None

    def load(self):
        if self.safety_checker is None:
            print("[Integrity] Loading Safety Checker...")
            from diffusers.pipelines.stable_diffusion import StableDiffusionSafetyChecker
            from transformers import CLIPImageProcessor
            
            self.safety_checker = StableDiffusionSafetyChecker.from_pretrained(
                "CompVis/stable-diffusion-safety-checker"
            ).to(self.device)
            self.feature_extractor = CLIPImageProcessor.from_pretrained(
                "openai/clip-vit-large-patch14"
            )

    def check(self, image: Image.Image) -> Tuple[Image.Image, bool]:
        """
        Check image for prohibited content. 
        Returns (processed_image, has_nsfw_concept)
        """
        self.load()
        
        # Convert PIL to numpy
        img_np = np.array(image)
        
        # Run safety check
        safety_checker_input = self.feature_extractor(image, return_tensors="pt").to(self.device)
        result_img, has_nsfw_concept = self.safety_checker(
            clip_input=safety_checker_input.pixel_values, 
            images=[img_np]
        )
        
        # result_img is a numpy array. If it's safe, it's the same image.
        # If unsafe, it's usually a black image.
        final_image = Image.fromarray(result_img[0].astype(np.uint8))
        
        return final_image, has_nsfw_concept[0]
