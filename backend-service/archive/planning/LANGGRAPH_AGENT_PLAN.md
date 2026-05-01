# 🧠 Phase 3: LangGraph Forensic Agent Implementation Plan

## 🎯 Objectives
Transform the SmartSketch ML Engine into a stateful, intelligent agent capable of maintaining forensic consistency across long, complex conversations.

## 🏛️ Architecture: The "Forensic Loop"
The system will move away from a linear "Prompt -> Image" flow to a "State -> Action -> Verification" loop.

### 1. The Forensic State (The "Suspect File")
We will use a structured state object to track the suspect's physical attributes.
- **Goal:** Prevent "Identity Drift."
- **Implementation:** A Pydantic-based `SuspectProfile` that persists across turns.
- **Attributes:** Age, Gender, Ethnicity, Face Shape, Eye Color/Shape, Nose Type, Hair Style/Color, Scars/Marks.

### 2. Agent Nodes (The "Brain Cells")
- **`AnalyzerNode`** (LLM): Interprets user intent and updates the Suspect Profile.
- **`RouterNode`** (Logic): Selects the optimal tool (Inpaint vs. Edit vs. Generate).
- **`ExecutionNode`** (ML): Triggers the `SmartSketchPipeline`.
- **`VerificationNode`** (Scrutinizer): Uses the `FaceScorer` (FaceNet) to mathematically verify forensic integrity. If the score is below the threshold (e.g., 0.8), the agent automatically triggers a re-generation with adjusted parameters.

## 💾 Persistence & Database Integration
- **Multi-Turn Context:** All chat history and the current `SuspectProfile` will be stored in a new `Conversation` model in Django.
- **LangGraph Checkpointing:** We will implement persistence to allow investigators to resume cases days later.

## 🛠️ Technical Stack
- **Framework:** `langgraph` (State management).
- **Orchestration:** `langchain` (LLM interaction).
- **Storage:** Django ORM / SQLite.
- **ML Engine:** Existing `SmartSketchPipeline`.

## 🏗️ Step-by-Step Implementation Plan

### Task 1: The Schema (Foundation) - ✅ COMPLETE
- **Action:** Define a Pydantic `SuspectProfile` class with attributes (age, eyes, hair, etc.).
- **Goal:** Create a "Type-Safe" suspect description.
- **Test:** [OK] Serialization/Deserialization verified. Prompt generation verified.

### Task 2: The Parser (The Intelligence) - ✅ COMPLETE
- **Action:** Build the `AnalyzerNode`. This LLM prompt takes the *current profile* + *new user message* and returns an *updated profile*.
- **Goal:** Handle relative changes (e.g., "darker," "older") correctly.
- **Test:** [OK] Verified that "blue eyes and black hair" surgically updates the profile state.

### Task 3: The Router (The Orchestration) - ✅ COMPLETE
- **Action:** Build the logic to select the tool.
    - If change is local (e.g., "glasses," "eyes") -> Route to **Inpainter**.
    - If change is structural (e.g., "age," "weight") -> Route to **Editor (ControlNet)**.
- **Goal:** Use the right tool for the job to maximize identity preservation.
- **Test:** [OK] Successfully routed forensic requests to the appropriate surgical vs. structural tools.

### Task 4: The Scrutinizer (Self-Correction) - ✅ COMPLETE
- **Action:** Build the `VerificationNode` loop.
- **Goal:** If the `FaceScorer` returns a score below 0.8, the agent automatically "backtracks" and retries the generation with a lower `strength`.
- **Test:** [OK] Verified automatic "Retry" logic when quality thresholds are not met.

### Task 5: The Persistence (The Memory Vault) - ✅ COMPLETE
- **Action:** Link LangGraph's `Checkpointer` to the Django database.
- **Goal:** Multi-session cases.
- **Implementation:** Created `DjangoCheckpointer` in `ml_engine/persistence.py` using `AgentCheckpoint` and `AgentStateWrite` models.
- **Test:** [OK] Verified that suspect identity (e.g., eye color) is preserved across multiple agent instances and server restarts.

---
*Last Updated: 2026-04-24*
