import cv2
import numpy as np
from PIL import Image, ImageFilter
import mediapipe as mp
from typing import List, Tuple, Optional

class FaceMasker:
    """
    Automated semantic masking for forensic edits using MediaPipe
    """
    def __init__(self):
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=True,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5
        )
        
        # Landmark indices for specific regions
        self.regions = {
            'eyes': [
                # Left eye
                33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246,
                # Right eye
                362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398
            ],
            'lips': [
                61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 308, 324, 318, 402, 317, 14, 87, 178, 88, 95, 185, 40, 39, 37, 0, 267, 269, 270, 409
            ],
            'nose': [
                1, 2, 98, 327, 278, 279, 4, 274, 275, 45, 115, 131, 10, 338, 297, 332, 284, 251, 389, 356, 454
            ],
            'brows': [
                70, 63, 105, 66, 107, 336, 296, 334, 293, 300, 46, 53, 52, 65, 55, 285, 295, 282, 283, 276
            ],
            'face': [
                10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136, 172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109, 10
            ]
        }

    def create_mask(self, image: Image.Image, target_region: str, dilation: int = 15, blur: int = 10) -> Optional[Image.Image]:
        """
        Create a binary mask for a specific region
        """
        # Convert PIL to CV2
        img_np = np.array(image)
        h, w, _ = img_np.shape
        
        # Detect landmarks
        results = self.face_mesh.process(img_np)
        
        if not results.multi_face_landmarks:
            print("[Masker] No face detected for masking.")
            return None
            
        landmarks = results.multi_face_landmarks[0].landmark
        
        # Determine which regions to include
        target_indices = []
        if target_region == 'all':
            for r in self.regions.values():
                target_indices.extend(r)
        elif target_region in self.regions:
            target_indices = self.regions[target_region]
        else:
            # Fuzzy match
            for r_name, r_indices in self.regions.items():
                if r_name in target_region.lower():
                    target_indices.extend(r_indices)
        
        if not target_indices:
            print(f"[Masker] Region '{target_region}' not recognized.")
            return None
            
        # Create blank mask
        mask = np.zeros((h, w), dtype=np.uint8)
        
        # Extract points for the mask
        points = []
        for idx in target_indices:
            pt = landmarks[idx]
            points.append([int(pt.x * w), int(pt.y * h)])
            
        # Draw convex hull for the points
        points = np.array(points)
        hull = cv2.convexHull(points)
        cv2.fillPoly(mask, [hull], 255)
        
        # Apply dilation to expand the mask slightly
        if dilation > 0:
            kernel = np.ones((dilation, dilation), np.uint8)
            mask = cv2.dilate(mask, kernel, iterations=1)
            
        # Convert back to PIL and apply blur for smooth edges
        mask_pil = Image.fromarray(mask)
        if blur > 0:
            mask_pil = mask_pil.filter(ImageFilter.GaussianBlur(radius=blur))
            
        return mask_pil

    def detect_region_from_prompt(self, prompt: str) -> str:
        """Heuristic to detect which region the prompt is talking about"""
        p = prompt.lower()
        if any(w in p for w in ['eye', 'glasses', 'spectacles', 'gaze']):
            return 'eyes'
        if any(w in p for w in ['lip', 'mouth', 'smile', 'teeth', 'lipstick']):
            return 'lips'
        if any(w in p for w in ['nose', 'nostril']):
            return 'nose'
        if any(w in p for w in ['brow', 'eyebrow']):
            return 'brows'
        if any(w in p for w in ['face', 'skin', 'age', 'cheek', 'wrinkle']):
            return 'face'
        return 'face' # Default to whole face if unsure
