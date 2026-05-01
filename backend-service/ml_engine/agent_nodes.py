"""
SmartSketch.AI - LangGraph Agent Nodes
Each class is a callable node in the forensic sketch workflow graph.
"""
import json
import re
import io
import base64
from typing import Dict, Any, Optional, List
from PIL import Image as PilImage

from .agent_state import ForensicAgentState, SuspectProfile


# ---------------------------------------------------------------------------
# 1. AnalyzerNode — reads user message, updates SuspectProfile
# ---------------------------------------------------------------------------

class AnalyzerNode:
    """
    Interprets user messages and updates the SuspectProfile via LLM
    (or a simple keyword heuristic when no LLM is configured).
    """

    def __init__(self, llm=None, remote_url: Optional[str] = None):
        self.llm = llm
        self.remote_url = remote_url

    def __call__(self, state: ForensicAgentState) -> Dict[str, Any]:
        print("\n--- ANALYZING USER INPUT ---")

        last_msg = state["messages"][-1]
        last_message = last_msg.content if hasattr(last_msg, "content") else str(last_msg)
        current_profile = state["suspect_profile"]

        system_prompt = self._build_system_prompt(current_profile)
        
        response_content = None
        try:
            if self.llm:
                response = self.llm.invoke([
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": last_message},
                ])
                response_content = response.content
            else:
                print("[Analyzer] No LLM configured - skipping to fallback/mock")
        except Exception as e:
            print(f"[Analyzer] Primary LLM failed: {e}. Attempting Modal fallback...")

        # --- Tier 2: Modal Fallback (Qwen on GPU) ---
        if response_content is None and self.remote_url:
            try:
                response_content = self._call_modal_analyze(system_prompt, last_message)
            except Exception as e:
                print(f"[Analyzer] Modal fallback failed: {e}")

        # --- Tier 3: Heuristic Mock (Final fallback) ---
        if response_content is None:
            print("[Analyzer] All LLMs failed. Using heuristic fallback.")
            return self._mock_llm_logic(last_message, current_profile)

        updated_profile_data = self._parse_json(response_content)

        intent = updated_profile_data.get("intent", "edit")
        enhanced = updated_profile_data.get("enhanced_prompt")
        negative = updated_profile_data.get("negative_prompt")
        age_params = updated_profile_data.get("age_params")
        profile_fields = updated_profile_data.get("profile", updated_profile_data)

        # Merge: keep existing fields if LLM omitted them
        base = current_profile.model_dump()
        base.update({k: v for k, v in profile_fields.items() if v is not None and k in base})
        updated_profile = SuspectProfile(**base)

        print(f"[Analyzer] Profile updated: {updated_profile.model_dump_json()}")
        print(f"[Analyzer] Intent: {intent} | Enhanced: {enhanced[:40] if enhanced else None} | Negative: {negative}")
        if age_params:
            print(f"[Analyzer] Age Params: {age_params}")
        
        return {
            "suspect_profile": updated_profile,
            "iteration_count": state["iteration_count"] + 1,
            "user_intent": intent,
            "enhanced_prompt": enhanced,
            "negative_prompt": negative,
            "age_params": age_params
        }

    def _build_system_prompt(self, profile: SuspectProfile) -> str:
        return f"""You are a Forensic Profile Manager and Semantic Router.
Analyze the user's message and the current suspect profile.

CURRENT PROFILE (JSON):
{profile.model_dump_json()}

INSTRUCTIONS:
1. Extract any facial attributes mentioned in the user's message and update the profile. Handle metaphors naturally (e.g. "face like a football" -> face_shape: "round").
2. Determine the user's INTENT from the following options:
   - "inpaint": The user wants to surgically change a specific feature (e.g., "change his eyes to blue", "add round glasses", "make the lips fuller").
   - "generate": The user indicates the current face is completely wrong or wants to start over (e.g., "start over", "erase that", "he looks nothing like that", "make him thinner").
   - "edit": The user wants to change structural or global features (e.g., "make him look older", "add a beard").
   - "age": The user wants to specifically see the person at a different age (e.g., "what would he look like in 10 years?", "make him look like he was in his 20s").
3. ENHANCE the prompt for SDXL:
   - Convert the user's description into a high-quality SDXL prompt using descriptive keywords (e.g. "rough face" -> "weathered skin, deep wrinkles, rugged complexion").
4. SMART NEGATIVE PROMPT:
   - Identify things the user explicitly DOES NOT want (e.g. "no beard" -> add "beard, facial hair" to negative prompt).
5. AGE PARAMETERS:
   - If the intent is "age", extract the relative change in years (positive for older, negative for younger).
6. Return ONLY a valid JSON object matching this schema:
{{
  "intent": "generate" | "edit" | "inpaint" | "age",
  "enhanced_prompt": "string",
  "negative_prompt": "string",
  "age_params": {{"years": number}} | null,
  "profile": {{ ... updated profile fields ... }}
}}"""

    def _parse_json(self, text: str) -> Dict[str, Any]:
        try:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception:
            pass
        return {}

    def _call_modal_analyze(self, system_prompt: str, user_message: str) -> Optional[str]:
        """Calls the /analyze endpoint on Modal to use Qwen as a fallback LLM."""
        import requests
        
        base = self.remote_url.rstrip("/")
        # Ensure we hit the base /analyze endpoint
        for suffix in ["/generate", "/edit", "/age", "/analyze"]:
            if base.endswith(suffix):
                base = base.rsplit("/", 1)[0]
        
        try:
            print(f"[Analyzer] Calling Modal fallback: {base}/analyze")
            resp = requests.post(
                f"{base}/analyze",
                json={
                    "system_prompt": system_prompt,
                    "user_message":  user_message
                },
                timeout=30 # LLM analysis should be fast
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("success"):
                    print("[Analyzer] ✅ Modal fallback successful")
                    return data.get("response")
        except Exception as e:
            print(f"[Analyzer] Modal request error: {e}")
        return None

    def _mock_llm_logic(self, message: str, profile: SuspectProfile) -> Dict[str, Any]:
        """Keyword heuristic for smoke-testing without a real LLM."""
        import re
        msg = message.lower()
        data = profile.model_dump()

        # --- Age ---
        age_match = re.search(r'mid[- ]?(\d+)s|early[- ]?(\d+)s|late[- ]?(\d+)s|(\d+)s\b|(\d+)[- ]?year', msg)
        if age_match:
            num = next(g for g in age_match.groups() if g is not None)
            low = int(num)
            data["age_range"] = f"{low}-{low + 9}"
        elif re.search(r'\b(\d{2,3})\b', msg):
            n = re.search(r'\b(\d{2,3})\b', msg).group(1)
            data["age_range"] = f"{n}-{int(n)+5}"

        # --- Gender ---
        if "male" in msg or " man" in msg:
            data["gender"] = "male"
        if "female" in msg or "woman" in msg:
            data["gender"] = "female"

        # --- Eyes ---
        if "blue" in msg and "eye" in msg:
            data["eye_color"] = "blue"
        if "brown" in msg and "eye" in msg:
            data["eye_color"] = "brown"
        if "green" in msg and "eye" in msg:
            data["eye_color"] = "green"

        # --- Hair colour ---
        if "black" in msg and "hair" in msg:
            data["hair_color"] = "black"
        if "brown" in msg and "hair" in msg:
            data["hair_color"] = "brown"
        if "blonde" in msg or "blond" in msg:
            data["hair_color"] = "blonde"
        if "grey" in msg or "gray" in msg:
            data["hair_color"] = "grey"

        # --- Hair style ---
        if "short" in msg and "hair" in msg:
            data["hair_style"] = "short"
        if "long" in msg and "hair" in msg:
            data["hair_style"] = "long"
        if "curly" in msg:
            data["hair_style"] = "curly"
        if "bald" in msg:
            data["hair_style"] = "bald"

        # --- Facial hair ---
        if "beard" in msg:
            data["facial_hair"] = "beard"
        if "mustache" in msg or "moustache" in msg:
            data["facial_hair"] = "mustache"
        if "clean shaven" in msg or "no beard" in msg:
            data["facial_hair"] = "none"

        # --- Distinctive features ---
        if "glasses" in msg or "spectacles" in msg:
            if "glasses" not in data["distinctive_features"]:
                data["distinctive_features"].append("glasses")
        if "scar" in msg and "scar" not in data["distinctive_features"]:
            data["distinctive_features"].append("scar")

        # --- Semantic Intent (Mock) ---
        intent = "edit"
        if any(w in msg for w in ["start over", "completely wrong", "wrong person", "restart"]):
            intent = "generate"
        elif any(w in msg for w in ["eye", "lip", "mouth", "nose", "brow", "glasses", "spectacles"]):
            intent = "inpaint"

        return {
            "suspect_profile": SuspectProfile(**data),
            "user_intent": intent,
            "enhanced_prompt": None,
            "negative_prompt": None,
            "age_params": None
        }


# ---------------------------------------------------------------------------
# 2. RouterNode — decides which ML tool to invoke
# ---------------------------------------------------------------------------

class RouterNode:
    """
    Selects the best ML operation based on which facial features changed.

    Routing logic:
      - No existing image → generate
      - Mention of precision local features (eyes, lips, nose, brows) → inpaint
      - All other edits → edit (ControlNet img2img for structural changes)
    """

    # Keywords that map to the inpainting path
    INPAINT_TRIGGERS = {
        "eyes": ["eye", "iris", "pupil", "gaze", "glasses", "spectacles"],
        "lips": ["lip", "mouth", "smile", "teeth"],
        "nose": ["nose", "nostril"],
        "brows": ["brow", "eyebrow"],
    }

    # Keywords that indicate the base identity is wrong and needs a fresh generation
    REGENERATE_TRIGGERS = [
        "start over", "completely wrong", "wrong person", "restart", 
        "different person", "not him", "not her", "regenerate", "looks nothing like"
    ]

    def __call__(self, state: ForensicAgentState) -> Dict[str, Any]:
        print("\n--- ROUTING TO ML TOOL ---")

        has_image = state.get("current_image") is not None

        # First turn: always generate from scratch
        if not has_image:
            print("[Router] No image yet → GENERATE")
            return {
                "next_step": "generate",
                "generation_params": {"target_region": None, "use_controlnet": False},
            }

        # Extract the last message text
        last_msg = state["messages"][-1]
        msg_text = (last_msg.content if hasattr(last_msg, "content") else str(last_msg)).lower()

        # 1. Hardware/UI bypass for immediate regeneration
        if msg_text == "[system_action: regenerate]":
            print("[Router] UI action detected → GENERATE (Resetting Identity)")
            return {
                "next_step": "generate",
                "generation_params": {"target_region": None, "use_controlnet": False},
            }

        # 2. LLM Semantic Routing
        user_intent = state.get("user_intent")
        if user_intent == "generate" or any(kw in msg_text for kw in self.REGENERATE_TRIGGERS):
            print("[Router] 'Wrong person' intent detected → GENERATE (Resetting Identity)")
            return {
                "next_step": "generate",
                "generation_params": {"target_region": None, "use_controlnet": False},
            }

        # 3. Age intent
        if user_intent == "age":
            print("[Router] Age intent detected → AGE")
            return {
                "next_step": "age",
                "generation_params": {"target_region": None, "use_controlnet": True},
            }

        # 4. Precision region triggers (LLM or Regex)
        target_region = None
        if user_intent == "inpaint":
            # Find which region
            for region, keywords in self.INPAINT_TRIGGERS.items():
                if any(kw in msg_text for kw in keywords):
                    target_region = region
                    break
            if not target_region:
                target_region = "face" # fallback if LLM said inpaint but didn't specify region
        else:
            # Fallback regex for inpaint
            for region, keywords in self.INPAINT_TRIGGERS.items():
                if any(kw in msg_text for kw in keywords):
                    target_region = region
                    user_intent = "inpaint"
                    break

        if target_region:
            print(f"[Router] Precision region detected → INPAINT  (region={target_region})")
            return {
                "next_step": "inpaint",
                "generation_params": {"target_region": target_region, "use_controlnet": False},
            }

        print("[Router] Structural/texture change → EDIT (ControlNet)")
        return {
            "next_step": "edit",
            "generation_params": {"target_region": None, "use_controlnet": True},
        }


# ---------------------------------------------------------------------------
# 3. VerificationNode — scores the output and decides to accept or retry
# ---------------------------------------------------------------------------

QUALITY_THRESHOLD = 55.0   # combined_score (0-100) below which we retry
MAX_RETRIES = 3


class VerificationNode:
    """
    Scores the generated/edited image using FaceScorer.
    Triggers a self-correction retry if quality is below threshold.
    """

    def __init__(self, scorer=None):
        self.scorer = scorer

    def __call__(self, state: ForensicAgentState) -> Dict[str, Any]:
        print("\n--- VERIFYING GENERATION QUALITY ---")

        current_b64  = state.get("current_image")
        iteration    = state.get("iteration_count", 0)

        # --- No scorer or no image: pass through ---
        if self.scorer is None or current_b64 is None:
            reason = "no scorer" if self.scorer is None else "no image in state"
            print(f"[Verifier] Skipping real score ({reason}) → accepting result")
            return {"next_step": "end", "is_verified": True, "last_score": None}

        # Decode base64 string → PIL Image for CLIP scoring
        try:
            current_image = PilImage.open(
                io.BytesIO(base64.b64decode(current_b64))
            ).convert("RGB")
        except Exception as dec_err:
            print(f"[Verifier] Could not decode image ({dec_err}) → accepting result")
            return {"next_step": "end", "is_verified": True, "last_score": None}

        # Build prompt from the current suspect profile for CLIP scoring
        profile = state.get("suspect_profile")
        prompt  = profile.to_detailed_prompt() if profile else "forensic face"

        # Get identity_score from state if the artist node saved it
        identity_score = state.get("generation_params", {}).get("last_identity_score")

        try:
            scores = self.scorer.score_generation(
                image=current_image,
                prompt=prompt,
                identity_score=identity_score,
            )
            combined = scores.get("combined_score", 0.0)
            print(f"[Verifier] combined_score={combined:.1f}  interpretation={scores.get('interpretation')}")

            if combined >= QUALITY_THRESHOLD:
                print(f"[Verifier] ✅ Quality accepted (score={combined:.1f})")
                return {"next_step": "end", "is_verified": True, "last_score": combined}

            if iteration < MAX_RETRIES:
                print(f"[Verifier] ⚠️ Low quality (score={combined:.1f}). Retrying [{iteration}/{MAX_RETRIES}] …")
                return {"next_step": "retry", "is_verified": False, "last_score": combined}

            print(f"[Verifier] Giving up after {iteration} attempts (score={combined:.1f})")
            return {"next_step": "end", "is_verified": False, "last_score": combined}

        except Exception as e:
            print(f"[Verifier] Scoring failed: {e} → accepting result")
            return {"next_step": "end", "is_verified": True, "last_score": None}
