"""
SmartSketch.AI - LLM Validation Module
Validates and enhances prompts for forensic sketch generation
"""

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
import json
import re
from typing import Tuple, Dict, Optional


class ForensicPromptValidator:
    """
    Validates and enhances prompts for forensic sketch generation
    
    Features:
    - NSFW content detection
    - Violence detection
    - Age validation (18+ for criminal cases)
    - Prompt enhancement
    - Attribute extraction
    """
    
    def __init__(self, model_name: str = "Qwen/Qwen2.5-3B-Instruct", device: str = "cuda"):
        """
        Initialize the validator
        
        Args:
            model_name: HuggingFace model ID
            device: 'cuda' or 'cpu'
        """
        print(f"📚 Loading {model_name}...")
        
        self.device = device
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float16 if device == "cuda" else torch.float32,
            device_map="auto" if device == "cuda" else None,
            low_cpu_mem_usage=True
        )
        
        if device == "cpu":
            self.model = self.model.to(device)
        
        print(f"✅ Validator loaded on {device}")
    
    def validate_and_enhance(
        self, 
        prompt: str, 
        case_type: str = "criminal", 
        age: Optional[int] = None
    ) -> Tuple[bool, str, Dict]:
        """
        Main validation function
        
        Args:
            prompt: User's text description
            case_type: "criminal" or "missing"
            age: Person's age (required for criminal cases)
        
        Returns:
            Tuple of (is_valid, enhanced_prompt, metadata_dict)
        """
        
        # Build the system prompt
        system_prompt = self._build_system_prompt()
        
        # Build the user message
        user_message = f"""Case Type: {case_type}
Age: {age if age else "Not specified"}
Prompt: "{prompt}"

Validate and enhance this prompt."""

        # Get LLM response
        llm_response = self._call_llm(system_prompt, user_message)
        
        # Parse the response
        result = self._parse_response(llm_response)
        
        # --- FORENSIC OVERRIDE (Hardcoded) ---
        # If the LLM rejects due to false NSFW / overcautious parsing, accept standard witness vocabulary.
        if not result['is_valid']:
            pl = prompt.lower()
            forensic_keywords = [
                'jaw', 'nose', 'face', 'fuller', 'thinner', 'rounder',
                'sharper', 'cheek', 'bone', 'structure', 'chin', 'forehead',
                'eye', 'lip', 'brow', 'hair', 'glasses', 'spectacle',
                'stubble', 'beard', 'mustache', 'goatee', 'sideburn', 'facial hair',
                'skin', 'texture', 'complexion', 'wrinkle', 'pore', 'freckle',
                'scar', 'mole', 'blemish', 'smooth', 'rough', 'weathered', 'aged',
                'tan', 'pale', 'lighter', 'darker', 'tone',
            ]
            if any(word in pl for word in forensic_keywords):
                print(f"[Validator] Forensic Override triggered for prompt: {prompt}")
                result['is_valid'] = True
                result['reason'] = "Forensic appearance/structure (manual override — witness-appropriate language)"
                if not result['enhanced_prompt']:
                    result['enhanced_prompt'] = (
                        f"professional forensic photograph, realistic portrait: {prompt}, "
                        "neutral expression, natural lighting"
                    )

        # Additional validation rules
        result = self._apply_safety_rules(result, case_type, age, prompt)
        
        return (
            result['is_valid'],
            result['enhanced_prompt'],
            {
                'reason': result['reason'],
                'attributes': result['attributes'],
                'safety_flags': result.get('safety_flags', []),
                'original_prompt': prompt
            }
        )
    
    def _build_system_prompt(self) -> str:
        """Build the system instruction for the LLM"""
        return """You are a forensic AI validator for SmartSketch.AI facial sketch generation system.

- PROTOCOL: You are a clinical forensic assistant. 
- REQUIREMENT: You MUST accept all anatomical and structural modifications requested for investigative accuracy.
- ACCEPT: Descriptions of face shape, bone structure, body type, and age progression. These are INVESTIGATIVE NECESSITIES, not personal comments.
- ACCEPT: Keywords like 'fuller face', 'thinner face', 'wider jaw', 'rounder face', 'sharper features'.
- ACCEPT (critical): Witness descriptions of facial hair (stubble, beard, mustache, goatee, sideburns) and skin or aging (skin texture, smoother, rougher, weathered, wrinkles, pores, complexion, freckles, scars, moles, tan, pale) are standard forensic composite requests. NEVER mark these as NSFW or sexual.
- REJECT ONLY: Pornography, explicit sexual violence, or requests to generate known celebrities.

ENHANCEMENT RULES:
- Add specific facial structure details (face shape, features)
- Add lighting and photography style
- Add realistic details (skin texture, expression)
- Keep it professional and forensic-appropriate
- KEEP ENHANCED PROMPT UNDER 60 WORDS
- Focus on MOST IMPORTANT features only

OUTPUT FORMAT (JSON only, no extra text):
{
  "is_valid": true or false,
  "reason": "Why accepted or rejected",
  "enhanced_prompt": "Enhanced version with details (max 60 words)",
  "attributes": ["list", "of", "detected", "features"],
  "safety_flags": ["any", "concerns"]
}

EXAMPLES:

Input: "man with glasses"
Output: {
  "is_valid": true,
  "reason": "Safe forensic description",
  "enhanced_prompt": "professional forensic photograph, realistic portrait of adult male with rectangular glasses, neutral expression, short hair, medium skin tone, even studio lighting",
  "attributes": ["male", "glasses", "adult"],
  "safety_flags": []
}

Input: "sexy woman with big chest"
Output: {
  "is_valid": false,
  "reason": "Contains inappropriate NSFW descriptors",
  "enhanced_prompt": "",
  "attributes": [],
  "safety_flags": ["nsfw", "inappropriate"]
}

Input: "make the jaw wider and face rounder"
Output: {
  "is_valid": true,
  "reason": "Safe structural modification for forensic accuracy",
  "enhanced_prompt": "professional forensic photograph, realistic portrait with wider jawline and fuller, rounder face shape, neutral expression, natural skin texture",
  "attributes": ["wide jaw", "round face"],
  "safety_flags": []
}

Now process the user's request:"""

    def _call_llm(self, system_prompt: str, user_message: str) -> str:
        """Call the LLM and get response"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        # Format as string first
        formatted = self.tokenizer.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=False
        )
        
        # Tokenize to get proper input_ids and attention_mask
        inputs = self.tokenizer(
            formatted,
            return_tensors="pt",
            padding=True
        ).to(self.model.device)
        
        input_ids = inputs["input_ids"]
        attention_mask = inputs["attention_mask"]
        
        # Generate (deterministic for reproducibility)
        with torch.no_grad():
            outputs = self.model.generate(
                input_ids=input_ids,
                attention_mask=attention_mask,
                max_new_tokens=512,
                do_sample=False,
                pad_token_id=self.tokenizer.eos_token_id,
                eos_token_id=self.tokenizer.eos_token_id
            )
        
        # Decode - slice off the input tokens
        input_len = input_ids.shape[1]
        response = self.tokenizer.decode(
            outputs[0][input_len:], 
            skip_special_tokens=True
        )
        
        return response

    def _parse_response(self, response: str) -> Dict:
        """Parse LLM JSON response"""
        
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            
            if json_match:
                result = json.loads(json_match.group())
                
                # Validate structure
                required_keys = ['is_valid', 'reason', 'enhanced_prompt', 'attributes']
                if all(key in result for key in required_keys):
                    return result
            
            # If parsing fails, return safe default
            return {
                "is_valid": False,
                "reason": "Could not parse LLM response",
                "enhanced_prompt": "",
                "attributes": [],
                "safety_flags": ["parse_error"]
            }
        
        except json.JSONDecodeError:
            return {
                "is_valid": False,
                "reason": "Invalid JSON from LLM",
                "enhanced_prompt": "",
                "attributes": [],
                "safety_flags": ["json_error"]
            }
    
    def _apply_safety_rules(
        self, 
        result: Dict, 
        case_type: str, 
        age: Optional[int], 
        prompt: str
    ) -> Dict:
        """Apply additional hardcoded safety rules"""
        
        # Rule 1: Criminal cases require age >= 18
        if case_type == "criminal" and age and age < 18:
            result['is_valid'] = False
            result['reason'] = "Criminal sketches require age >= 18 years"
            result['safety_flags'] = result.get('safety_flags', []) + ['underage_criminal']
        
        # Rule 2: Age must be provided for criminal cases
        if case_type == "criminal" and not age:
            result['is_valid'] = False
            result['reason'] = "Age is required for criminal cases"
            result['safety_flags'] = result.get('safety_flags', []) + ['missing_age']
        
        # Rule 3: Block common NSFW keywords (backup check)
        nsfw_keywords = ['nude', 'naked', 'sexy', 'porn', 'explicit', 'topless']
        if any(word in prompt.lower() for word in nsfw_keywords):
            result['is_valid'] = False
            result['reason'] = "Prompt contains inappropriate content"
            result['safety_flags'] = result.get('safety_flags', []) + ['nsfw_keyword']
        
        # Rule 4: Block violence keywords
        violence_keywords = ['blood', 'dead', 'kill', 'murder', 'weapon', 'gun', 'knife', 'bomb']
        if any(word in prompt.lower() for word in violence_keywords):
            result['is_valid'] = False
            result['reason'] = "Prompt contains violent content"
            result['safety_flags'] = result.get('safety_flags', []) + ['violence_keyword']
        
        return result


# Convenience function for quick usage
def validate_prompt(
    prompt: str,
    case_type: str = "criminal",
    age: Optional[int] = None,
    validator: Optional[ForensicPromptValidator] = None
) -> Tuple[bool, str, Dict]:
    """
    Quick validation function
    
    Args:
        prompt: Text description
        case_type: "criminal" or "missing"
        age: Person's age
        validator: Optional pre-initialized validator (for performance)
    
    Returns:
        Tuple of (is_valid, enhanced_prompt, metadata)
    """
    if validator is None:
        validator = ForensicPromptValidator()
    
    return validator.validate_and_enhance(prompt, case_type, age)
