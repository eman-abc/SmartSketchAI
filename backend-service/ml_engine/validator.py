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

Your job is to:
1. Check if the prompt is SAFE (reject if contains violence, NSFW content, hate speech, illegal requests)
2. Check if the prompt is APPROPRIATE for forensic use
3. ENHANCE the prompt by adding realistic facial details for better generation

SAFETY RULES:
- REJECT: Violence, weapons, NSFW, nudity, hate speech, minors in inappropriate contexts
- REJECT: Celebrity names or identifiable real people
- ACCEPT: Professional forensic descriptions (age, gender, facial features, hair, accessories)

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

Now process the user's request:"""

    def _call_llm(self, system_prompt: str, user_message: str) -> str:
        """Call the LLM and get response"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        # Format for Llama/Qwen
        input_ids = self.tokenizer.apply_chat_template(
            messages,
            add_generation_prompt=True,
            return_tensors="pt"
        ).to(self.model.device)
        
        # Generate (deterministic for reproducibility)
        with torch.no_grad():
            outputs = self.model.generate(
                input_ids,
                max_new_tokens=512,
                do_sample=False,  # Deterministic greedy decoding
                pad_token_id=self.tokenizer.eos_token_id,
                eos_token_id=self.tokenizer.eos_token_id
            )
        
        # Decode
        response = self.tokenizer.decode(
            outputs[0][input_ids.shape[1]:], 
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
