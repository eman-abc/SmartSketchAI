from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Annotated, Any
from typing_extensions import TypedDict
import operator


class SuspectProfile(BaseModel):
    """Structured representation of a suspect's facial features."""
    gender:    str = Field(default="unknown", description="Gender of the suspect")
    age_range: str = Field(default="unknown", description="Estimated age range")
    ethnicity: str = Field(default="unknown", description="Estimated ethnicity")
    face_shape: str = Field(default="neutral", description="Shape of the face (oval, square, etc.)")

    # Eyes
    eye_color: str  = Field(default="neutral", description="Color of the eyes")
    eye_shape: str  = Field(default="neutral", description="Shape/set of the eyes")
    eyebrows:  str  = Field(default="neutral", description="Style of eyebrows")

    # Hair
    hair_style:  str = Field(default="neutral", description="Style of head hair")
    hair_color:  str = Field(default="neutral", description="Color of head hair")
    facial_hair: str = Field(default="none",    description="Beard, mustache, etc.")

    # Other features
    nose_type:  str       = Field(default="neutral", description="Shape of the nose")
    mouth_type: str       = Field(default="neutral", description="Shape of the lips/mouth")
    distinctive_features: List[str] = Field(
        default_factory=list, description="Scars, moles, tattoos, glasses"
    )

    def to_detailed_prompt(self) -> str:
        """Convert the structured profile into a descriptive prompt string for SDXL."""
        SKIP = {"unknown", "neutral", "none", ""}
        parts = []

        if self.gender    not in SKIP: parts.append(f"a {self.gender}")
        if self.age_range not in SKIP: parts.append(f"aged {self.age_range}")
        if self.ethnicity not in SKIP: parts.append(f"of {self.ethnicity} ethnicity")
        if self.face_shape not in SKIP: parts.append(f"with {self.face_shape} face shape")

        # Eyes
        eye_desc = " ".join(p for p in [self.eye_color, self.eye_shape] if p not in SKIP)
        if eye_desc:
            parts.append(f"{eye_desc} eyes")

        # Hair
        hair_desc = " ".join(p for p in [self.hair_color, self.hair_style] if p not in SKIP)
        if hair_desc:
            parts.append(f"{hair_desc} hair")

        if self.facial_hair not in SKIP: parts.append(f"with {self.facial_hair}")
        if self.nose_type   not in SKIP: parts.append(f"a {self.nose_type} nose")
        if self.mouth_type  not in SKIP: parts.append(f"{self.mouth_type} lips")

        if self.distinctive_features:
            parts.append(f"distinctive features: {', '.join(self.distinctive_features)}")

        return ", ".join(parts) if parts else "a person"


class ForensicAgentState(TypedDict):
    """The shared state of the LangGraph Agent."""

    # Messages use the operator.add reducer to keep a running history
    messages: Annotated[List[Any], operator.add]

    # The structured suspect profile (updated by AnalyzerNode each turn)
    suspect_profile: SuspectProfile

    # Current visual state
    current_image: Optional[Any]   # PIL Image object
    generation_id: Optional[str]

    # NLP Semantic Routing
    user_intent: Optional[str]     # 'generate' | 'edit' | 'inpaint' | None

    # Routing & execution parameters (set by RouterNode)
    next_step: str                 # 'generate' | 'edit' | 'inpaint' | 'retry' | 'end'
    generation_params: Optional[Dict]  # e.g. {"target_region": "eyes", "use_controlnet": True}

    # Verification results (set by VerificationNode)
    is_verified: bool
    last_score: Optional[float]    # combined quality score from last verification pass

    # Error tracking
    last_error: Optional[str]

    # Loop counter (prevent infinite retry loops)
    iteration_count: int
