"""
SmartSketch.AI - LangGraph Agent
Assembled forensic sketch workflow graph.
"""
import io
import base64
import requests
import traceback
from typing import Dict, Any, List, Optional
from PIL import Image as PilImage

from langgraph.graph import StateGraph, END

from .agent_state import ForensicAgentState, SuspectProfile
from .agent_nodes import AnalyzerNode, RouterNode, VerificationNode
from .critic import ForensicCriticClient
from .persistence import DjangoCheckpointer


class SmartSketchAgent:
    """
    LangGraph agent that orchestrates the full forensic sketch workflow:

      analyze → route → artist → verify → (retry | end)

    The artist node dispatches to the correct pipeline method:
      - generate  → pipeline.generate_sketch()
      - edit      → pipeline.edit_sketch()     (ControlNet img2img)
      - inpaint   → pipeline.inpainting_edit() (semantic mask inpainting)
    """

    def __init__(
        self,
        llm=None,
        pipeline=None,
        checkpointer=None,
        remote_url: Optional[str] = None,
    ):
        self.llm        = llm
        self.pipeline   = pipeline
        self.remote_url = remote_url

        self.checkpointer = checkpointer or DjangoCheckpointer()

        # Nodes
        self.analyzer = AnalyzerNode(llm=llm, remote_url=remote_url)
        self.router   = RouterNode()
        self.verifier = VerificationNode(
            scorer=pipeline.scorer if pipeline else None,
            critic_client=ForensicCriticClient(remote_url=remote_url),
        )

        # Graph
        wf = StateGraph(ForensicAgentState)
        wf.add_node("analyze", self.analyzer)
        wf.add_node("route",   self.router)
        wf.add_node("artist",  self._artist_node)
        wf.add_node("verify",  self.verifier)

        wf.set_entry_point("analyze")
        wf.add_edge("analyze", "route")

        wf.add_conditional_edges(
            "route",
            lambda x: x["next_step"],
            {"generate": "artist", "edit": "artist", "inpaint": "artist", "age": "artist"},
        )

        wf.add_edge("artist", "verify")

        wf.add_conditional_edges(
            "verify",
            lambda x: x["next_step"],
            {"retry": "artist", "end": END},
        )

        self.app = wf.compile(checkpointer=self.checkpointer)

    # ------------------------------------------------------------------
    # Artist node — the only place ML inference happens
    # ------------------------------------------------------------------

    def _artist_node(self, state: ForensicAgentState) -> Dict[str, Any]:
        """Dispatch to the correct ML pipeline method based on next_step."""
        action = state.get("next_step", "generate")
        print(f"\n--- ML ARTIST: {action.upper()} ---")

        # ---- Remote Modal path (primary when remote_url is set) ----
        if self.remote_url:
            result = self._call_remote(state, action)
            if result is not None:
                return result
            print("[Artist] Remote call failed – falling back to local pipeline")

        # ---- Local pipeline path ----
        if self.pipeline is None:
            print("[Artist] No local pipeline available; returning mock")
            return {"current_image": None, "last_error": "No pipeline configured"}

        try:
            if action == "generate":
                return self._local_generate(state)
            elif action == "edit":
                return self._local_edit(state)
            elif action == "age":
                return self._local_age(state)
            elif action in ("inpaint", "retry"):
                return self._local_inpaint(state)
            else:
                return {"last_error": f"Unknown action: {action}"}
        except Exception as e:
            traceback.print_exc()
            return {"last_error": str(e)}

    # ------------------------------------------------------------------
    # Remote (Modal ML service) call
    # ------------------------------------------------------------------

    def _call_remote(self, state: ForensicAgentState, action: str) -> Optional[Dict[str, Any]]:
        """
        Send a request to the Modal ML service.
        Returns a state-update dict or None on failure.
        """
        import base64, io as _io
        from PIL import Image as _Image

        profile: SuspectProfile = state.get("suspect_profile") or SuspectProfile()
        prompt = profile.to_detailed_prompt()

        if action == "age":
            try:
                return self._call_remote_age(state)
            except Exception as e:
                print(f"[Artist/remote/age] {e}")
                return None

        # ---- /generate ----
        if action == "generate":
            try:
                resp = requests.post(
                    f"{self.remote_url.rstrip('/').replace('/generate','').replace('/edit','')}/generate",
                    json={
                        "prompt": state.get("enhanced_prompt") or prompt,
                        "negative_prompt": state.get("negative_prompt"),
                        "case_type": "criminal",
                        "age": 30
                    },
                    timeout=180,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("success") and data.get("image_base64"):
                        img_bytes = base64.b64decode(data["image_base64"])
                        pil_img   = _Image.open(_io.BytesIO(img_bytes)).convert("RGB")
                        return {
                            "current_image": pil_img,
                            "generation_id": data.get("generation_id"),
                            "critic_report": data.get("critic_report"),
                            "generation_params": {
                                **(state.get("generation_params") or {}),
                                "last_identity_score": None,
                            },
                        }
            except Exception as e:
                print(f"[Artist/remote/generate] {e}")
            return None

        # ---- /edit or /inpaint (both hit /edit on the remote Modal service) ----
        current_image = state.get("current_image")
        if current_image is None:
            return None

        last_msg = state["messages"][-1]
        edit_prompt = (
            state.get("critic_adjustment_prompt")
            or state.get("enhanced_prompt")
            or (last_msg.content if hasattr(last_msg, "content") else str(last_msg))
        )

        # Encode image
        buf = _io.BytesIO()
        if isinstance(current_image, str):
            current_image = self._b64_to_pil(current_image)
        current_image.save(buf, format="PNG")
        img_b64 = base64.b64encode(buf.getvalue()).decode()

        try:
            base = self.remote_url.rstrip("/")
            if base.endswith("/generate") or base.endswith("/edit"):
                base = base.rsplit("/", 1)[0]
            resp = requests.post(
                f"{base}/edit",
                json={
                    "generation_id": state.get("generation_id", "agent"),
                    "original_image": img_b64,
                    "edit_prompt":    edit_prompt,
                    "negative_prompt": state.get("negative_prompt"),
                    "strength":       0.65,
                },
                timeout=180,
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("success") and data.get("edited_image"):
                    edited_bytes = base64.b64decode(data["edited_image"])
                    pil_edited   = _Image.open(_io.BytesIO(edited_bytes)).convert("RGB")
                    return {
                        "current_image": pil_edited,
                        "generation_id": data.get("edit_id", state.get("generation_id")),
                        "critic_report": data.get("critic_report"),
                        "generation_params": {
                            **(state.get("generation_params") or {}),
                            "last_identity_score": data.get("identity_score"),
                        },
                    }
        except Exception as e:
            print(f"[Artist/remote/edit] {e}")
        return None

    def _call_remote_age(self, state: ForensicAgentState) -> Optional[Dict[str, Any]]:
        """Call the /age endpoint on Modal."""
        import base64, io as _io
        from PIL import Image as _Image

        current_image = state.get("current_image")
        if current_image is None:
            return None

        # Encode image
        buf = _io.BytesIO()
        if isinstance(current_image, str):
            current_image = self._b64_to_pil(current_image)
        current_image.save(buf, format="PNG")
        img_b64 = base64.b64encode(buf.getvalue()).decode()

        age_params = state.get("age_params") or {"years": 10}

        try:
            base = self.remote_url.rstrip("/")
            if base.endswith("/generate") or base.endswith("/edit") or base.endswith("/age"):
                base = base.rsplit("/", 1)[0]
            
            resp = requests.post(
                f"{base}/age",
                json={
                    "generation_id": state.get("generation_id", "agent"),
                    "original_image": img_b64,
                    "years":          age_params.get("years", 10),
                    "prompt":         state.get("enhanced_prompt"),
                },
                timeout=180,
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("success") and data.get("edited_image"):
                    edited_bytes = base64.b64decode(data["edited_image"])
                    pil_edited   = _Image.open(_io.BytesIO(edited_bytes)).convert("RGB")
                    return {
                        "current_image": pil_edited,
                        "generation_id": data.get("edit_id", state.get("generation_id")),
                        "critic_report": data.get("critic_report"),
                        "generation_params": {
                            **(state.get("generation_params") or {}),
                            "last_identity_score": data.get("identity_score"),
                        },
                    }
        except Exception as e:
            print(f"[Artist/remote/age] {e}")
        return None

    # ------------------------------------------------------------------
    # Serialization helpers — PIL Image ↔ base64 string
    # LangGraph checkpointers (MemorySaver, DjangoCheckpointer) cannot
    # serialize raw PIL Image objects. Store images as base64 strings in
    # state and decode only when calling the ML pipeline.
    # ------------------------------------------------------------------

    @staticmethod
    def _pil_to_b64(img: PilImage.Image) -> str:
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode("utf-8")

    @staticmethod
    def _b64_to_pil(b64: str) -> PilImage.Image:
        return PilImage.open(io.BytesIO(base64.b64decode(b64))).convert("RGB")

    # ------------------------------------------------------------------
    # Local pipeline helpers
    # ------------------------------------------------------------------

    def _local_generate(self, state: ForensicAgentState) -> Dict[str, Any]:
        import re
        profile: SuspectProfile = state.get("suspect_profile") or SuspectProfile()
        prompt = profile.to_detailed_prompt()
        print(f"[Artist/local/generate] prompt: {prompt}")

        age: int = 30
        if profile.age_range and profile.age_range not in ("unknown", "neutral"):
            nums = re.findall(r'\d+', profile.age_range)
            if nums:
                age = int(nums[0])

        result = self.pipeline.generate_sketch(
            prompt=state.get("critic_adjustment_prompt") or state.get("enhanced_prompt") or prompt,
            negative_prompt=state.get("negative_prompt"),
            case_type="criminal",
            age=age,
            output_type="photo",
        )
        if not result.get("success"):
            return {"last_error": result.get("error", "Generation failed")}

        # Store as base64 string — PIL Image is not checkpoint-serializable
        return {
            "current_image": self._pil_to_b64(result["image"]),
            "generation_id": result["generation_id"],
            "last_error": None,
            "generation_params": {
                **(state.get("generation_params") or {}),
                "last_identity_score": None,
            },
        }

    def _local_edit(self, state: ForensicAgentState) -> Dict[str, Any]:
        current_b64 = state.get("current_image")
        if current_b64 is None:
            return self._local_generate(state)

        # Decode base64 → PIL for the pipeline call
        current_image = self._b64_to_pil(current_b64)

        last_msg = state["messages"][-1]
        edit_prompt = last_msg.content if hasattr(last_msg, "content") else str(last_msg)
        edit_prompt = state.get("critic_adjustment_prompt") or state.get("enhanced_prompt") or edit_prompt
        print(f"[Artist/local/edit] prompt: {edit_prompt}")

        result = self.pipeline.edit_sketch(
            generation_id=state.get("generation_id", "unknown"),
            original_image=current_image,
            edit_prompt=edit_prompt,
            negative_prompt=state.get("negative_prompt"),
        )
        if not result.get("success"):
            return {"last_error": result.get("error", "Edit failed")}

        return {
            "current_image": self._pil_to_b64(result["edited_image"]),
            "generation_id": result.get("edit_id", state.get("generation_id")),
            "last_error": None,
            "generation_params": {
                **(state.get("generation_params") or {}),
                "last_identity_score": result.get("identity_score"),
            },
        }

    def _local_age(self, state: ForensicAgentState) -> Dict[str, Any]:
        current_b64 = state.get("current_image")
        if current_b64 is None:
            return self._local_generate(state)

        # Decode base64 → PIL for the pipeline call
        current_image = self._b64_to_pil(current_b64)

        age_params = state.get("age_params") or {"years": 10}
        print(f"[Artist/local/age] years: {age_params.get('years')}")

        result = self.pipeline.age_progression(
            generation_id=state.get("generation_id", "unknown"),
            original_image=current_image,
            years=age_params.get("years", 10),
            enhanced_prompt=state.get("critic_adjustment_prompt") or state.get("enhanced_prompt")
        )
        if not result.get("success"):
            return {"last_error": result.get("error", "Age progression failed")}

        return {
            "current_image": self._pil_to_b64(result["edited_image"]),
            "generation_id": result.get("edit_id", state.get("generation_id")),
            "last_error": None,
            "generation_params": {
                **(state.get("generation_params") or {}),
                "last_identity_score": result.get("identity_score"),
            },
        }

    def _local_inpaint(self, state: ForensicAgentState) -> Dict[str, Any]:
        import re
        current_b64 = state.get("current_image")
        if current_b64 is None:
            return self._local_generate(state)

        # Decode base64 → PIL for the pipeline call
        current_image = self._b64_to_pil(current_b64)

        last_msg = state["messages"][-1]
        raw_msg = last_msg.content if hasattr(last_msg, "content") else str(last_msg)

        # Build a forensic descriptor instead of passing raw conversational text.
        # The validator rejects phrases like "He was wearing round glasses".
        profile: SuspectProfile = state.get("suspect_profile") or SuspectProfile()
        base_desc = profile.to_detailed_prompt()
        target_region = (state.get("generation_params") or {}).get("target_region")

        # Extract the key feature word(s) from the raw message for the edit prompt
        feature_phrase = raw_msg  # fallback
        kw_map = {
            "glasses": "wearing round glasses",
            "spectacles": "wearing round glasses",
            "blue eye": "blue eyes",
            "green eye": "green eyes",
            "lip": "fuller lips",
            "nose": "broader nose",
            "brow": "thick eyebrows",
        }
        for kw, phrase in kw_map.items():
            if kw in raw_msg.lower():
                feature_phrase = phrase
                break

        edit_prompt = f"{base_desc}, {feature_phrase}"
        print(f"[Artist/local/inpaint] region={target_region}  prompt: {edit_prompt}")

        # Extract age from profile for validator
        age: int = 30
        if profile.age_range and profile.age_range not in ("unknown", "neutral"):
            nums = re.findall(r'\d+', profile.age_range)
            if nums:
                age = int(nums[0])

        result = self.pipeline.inpainting_edit(
            generation_id=state.get("generation_id", "unknown"),
            original_image=current_image,
            edit_prompt=state.get("critic_adjustment_prompt") or state.get("enhanced_prompt") or edit_prompt,
            negative_prompt=state.get("negative_prompt"),
            target_region=target_region,
            age=age,
        )
        if not result.get("success"):
            return {"last_error": result.get("error", "Inpainting failed")}

        return {
            "current_image": self._pil_to_b64(result["edited_image"]),
            "generation_id": result.get("edit_id", state.get("generation_id")),
            "last_error": None,
            "generation_params": {
                **(state.get("generation_params") or {}),
                "last_identity_score": result.get("identity_score"),
            },
        }

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run(self, message: str, thread_id: str = "default") -> Dict[str, Any]:
        """Run a single conversational turn and return the final state."""
        config = {"configurable": {"thread_id": thread_id}}

        current_state = self.app.get_state(config)
        inputs: Dict[str, Any] = {"messages": [message]}

        if not current_state.values:
            # First turn — initialise state
            inputs["suspect_profile"]   = SuspectProfile()
            inputs["iteration_count"]   = 0
            inputs["next_step"]         = "analyze"
            inputs["current_image"]     = None
            inputs["generation_id"]     = None
            inputs["generation_params"] = {}
            inputs["is_verified"]       = False
            inputs["last_score"]        = None
            inputs["last_error"]        = None
            inputs["critic_report"]     = None
            inputs["critic_adjustment_prompt"] = None
            inputs["critic_attempts"]   = 0
            inputs["verification_history"] = []

        return self.app.invoke(inputs, config)
