"""
SmartSketch.AI - Scoring Module
Scores generated faces using CLIP for semantic alignment
"""

import torch
import clip
from PIL import Image
from typing import Dict, Optional


class FaceScorer:
    """
    Scores generated faces using CLIP
    
    Features:
    - Semantic text-image alignment (CLIP)
    - Quality scoring (0-100 scale)
    - Interpretation (Excellent/Good/Fair/Poor)
    """
    
    def __init__(self, model_name: str = "ViT-B/32", device: str = "cuda"):
        """
        Initialize the scorer
        
        Args:
            model_name: CLIP model name
            device: 'cuda' or 'cpu'
        """
        print(f"📊 Loading CLIP {model_name}...")
        
        self.device = device if torch.cuda.is_available() else "cpu"
        self.clip_model, self.clip_preprocess = clip.load(model_name, device=self.device)
        self.clip_model.eval()
        
        print(f"✅ Scorer loaded on {self.device}")
    
    def score_generation(
        self, 
        image: Image.Image, 
        prompt: str, 
        identity_score: Optional[float] = None
    ) -> Dict:
        """
        Score a generated image
        
        Args:
            image: PIL Image
            prompt: Text description
            identity_score: Score for identity preservation (optional)
        
        Returns:
            Dictionary with scores and interpretation
        """
        clip_score = self.compute_clip_score(image, prompt)
        return self.get_combined_score(clip_score, identity_score=identity_score)
    
    def compute_clip_score(self, image: Image.Image, text_prompt: str) -> float:
        """
        Compute semantic alignment between image and text
        
        Args:
            image: PIL Image
            text_prompt: Text description
        
        Returns:
            Score between 0 and 1 (higher = better match)
        """
        # Truncate prompt if needed
        truncated_prompt = self._truncate_prompt(text_prompt)
        
        # Preprocess
        image_input = self.clip_preprocess(image).unsqueeze(0).to(self.device)
        text_input = clip.tokenize([truncated_prompt], truncate=True).to(self.device)
        
        # Compute similarity
        with torch.no_grad():
            image_features = self.clip_model.encode_image(image_input)
            text_features = self.clip_model.encode_text(text_input)
            image_features /= image_features.norm(dim=-1, keepdim=True)
            text_features /= text_features.norm(dim=-1, keepdim=True)
            similarity = (image_features @ text_features.T).item()
        
        # Normalize to 0-1
        return (similarity + 1) / 2
    
    def get_combined_score(
        self, 
        clip_score: float, 
        identity_score: Optional[float] = None
    ) -> Dict:
        """
        Combine scores into final evaluation
        
        Args:
            clip_score: Semantic alignment score (0-1)
            identity_score: Identity preservation score (0-1, optional)
        
        Returns:
            Dictionary with scores and interpretation
        """
        if identity_score is None:
            combined = clip_score * 100
        else:
            # Weighted combination: 60% semantic + 40% identity
            combined = (0.6 * clip_score + 0.4 * identity_score) * 100
        
        return {
            "clip_score": round(clip_score, 3),
            "identity_score": round(identity_score, 3) if identity_score else None,
            "combined_score": round(combined, 2),
            "interpretation": self._interpret_score(combined)
        }
    
    def _truncate_prompt(self, text: str, max_length: int = 76) -> str:
        """
        Truncate prompt to fit CLIP's 77 token limit
        
        Args:
            text: Input text
            max_length: Maximum tokens (default 76, reserve 1 for special token)
        
        Returns:
            Truncated text
        """
        try:
            tokens = clip.tokenize([text], truncate=False)
            if tokens.shape[1] <= 77:
                return text
        except RuntimeError:
            pass
        
        # Truncate by words
        words = text.split()
        truncated = []
        
        for word in words:
            test_text = " ".join(truncated + [word])
            try:
                clip.tokenize([test_text], truncate=False)
                truncated.append(word)
            except RuntimeError:
                break
        
        return " ".join(truncated)
    
    def _interpret_score(self, score: float) -> str:
        """
        Give human-readable interpretation of score
        
        Args:
            score: Combined score (0-100)
        
        Returns:
            Quality interpretation string
        """
        if score >= 80:
            return "Excellent - High quality match"
        elif score >= 60:
            return "Good - Acceptable quality"
        elif score >= 40:
            return "Fair - May need refinement"
        else:
            return "Poor - Consider regenerating"


# Convenience function for quick usage
def score_image(
    image: Image.Image,
    prompt: str,
    scorer: Optional[FaceScorer] = None
) -> Dict:
    """
    Quick scoring function
    
    Args:
        image: PIL Image to score
        prompt: Text description
        scorer: Optional pre-initialized scorer (for performance)
    
    Returns:
        Dictionary with scores and interpretation
    """
    if scorer is None:
        scorer = FaceScorer()
    
    return scorer.score_generation(image, prompt)
