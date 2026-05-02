import hashlib
import numpy as np
from PIL import Image
import os
from typing import Tuple
from imwatermark import WatermarkEncoder, WatermarkDecoder

class ForensicSigner:
    def __init__(self, watermark_text: str = "SMARTSKETCH_AI"):
        self.watermark_text = watermark_text
        self.encoder = WatermarkEncoder()
        self.encoder.set_watermark('bytes', watermark_text.encode('utf-8'))
        self.method = 'dwtDct'

    def sign_image(self, image: Image.Image) -> Image.Image:
        try:
            img_np = np.array(image)
            print(f"[Integrity] Embedding invisible watermark: {self.watermark_text}")
            signed_img_np = self.encoder.encode(img_np, self.method)
            return Image.fromarray(signed_img_np.astype(np.uint8))
        except Exception as e:
            print(f"[!] Watermarking failed: {e}. Returning original image.")
            return image

    def calculate_hash(self, image: Image.Image) -> str:
        img_bytes = image.tobytes()
        sha256_hash = hashlib.sha256(img_bytes).hexdigest()
        print(f"[Integrity] Forensic Hash: {sha256_hash}")
        return sha256_hash

    def verify_watermark(self, image: Image.Image) -> bool:
        try:
            img_np = np.array(image)
            decoder = WatermarkDecoder('bytes', len(self.watermark_text.encode('utf-8')) * 8)
            decoded = decoder.decode(img_np, self.method)
            return decoded.decode('utf-8') == self.watermark_text
        except:
            return False


class ForensicSafetyChecker:
    def __init__(self, device="cuda"):
        self.device = device
        self.safety_checker = None
        self.feature_extractor = None

    def load(self):
        if self.safety_checker is None:
            try:
                print("[Integrity] Loading Safety Checker...")
                from diffusers.pipelines.stable_diffusion import StableDiffusionSafetyChecker
                from transformers import CLIPImageProcessor
                self.safety_checker = StableDiffusionSafetyChecker.from_pretrained(
                    "CompVis/stable-diffusion-safety-checker"
                ).to(self.device)
                self.feature_extractor = CLIPImageProcessor.from_pretrained(
                    "openai/clip-vit-large-patch14"
                )
            except Exception as e:
                print(f"[Integrity] Safety checker failed to load ({e}), disabling.")
                self.safety_checker = None
                self.feature_extractor = None

    def check(self, image: Image.Image) -> Tuple[Image.Image, bool]:
        try:
            self.load()
        except Exception as e:
            print(f"[Integrity] Safety check skipped: {e}")
            return image, False

        if self.safety_checker is None or self.feature_extractor is None:
            return image, False

        try:
            img_np = np.array(image)
            safety_checker_input = self.feature_extractor(image, return_tensors="pt").to(self.device)
            result_img, has_nsfw_concept = self.safety_checker(
                clip_input=safety_checker_input.pixel_values,
                images=[img_np]
            )
            final_image = Image.fromarray(result_img[0].astype(np.uint8))
            return final_image, has_nsfw_concept[0]
        except Exception as e:
            print(f"[Integrity] Safety check failed ({e}), returning original.")
            return image, False
