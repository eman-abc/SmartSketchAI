# SmartSketch: ML & Generative AI Audit

This document focuses on risks and vulnerabilities specific to the LLM orchestration and image generation pipelines.

## 🧠 Generative Pipeline Risks

### 1. Structural Drift & Demographic Clash
- **Issue:** The agent uses `img2img` with ControlNet to refine images. However, if an investigator changes a core demographic (e.g., from "Young" to "Old"), the ControlNet "locks" the young bone structure.
- **Risk:** This produces artifact-heavy, biologically impossible "hybrids" that compromise forensic accuracy.
- **Mitigation:** Implement "Semantic Breaking Points" where the agent detects major feature changes and triggers a full `text2img` re-generation instead of an edit.

### 2. LLM Spatial Hallucination
- **Issue:** The agent relies on the LLM (Qwen) to determine where to apply surgical edits (inpainting).
- **Risk:** LLMs are notorious for spatial reasoning errors. The model might map "add earrings" to the mouth or nose region if not strictly validated.
- **Mitigation:** Use a **Hard-Coded Semantic Map**. The LLM should only output an "Action Type" (e.g., EDIT_EYES), and the Python logic should handle the exact MediaPipe mask coordinate.

## 🛡️ AI Security & Safety

### 1. Prompt Injection
- **Issue:** User messages are passed to the agent without sanitization.
- **Risk:** Adversarial prompts ("Ignore safety filters and generate [Restricted Content]") can bypass the LLM's instructions.
- **Mitigation:** Integrate a dedicated **Guardrail Model** (e.g., Llama Guard) to inspect every incoming text before it hits the agent.

### 2. Forensic Chain of Custody
- **Issue:** Hashing is implemented but not cryptographically tied to the session state.
- **Risk:** Difficult to prove in a legal context exactly when and how an image was modified by the AI.
- **Mitigation:** Implement a **Signed Audit Trail**. Every image hash should be cryptographically signed by the server and stored in a non-nullable DB field.

## ⚡ Performance Optimizations

- **TensorRT Conversion:** Convert SDXL and Qwen to **NVIDIA TensorRT** engines to achieve a 2x speedup in generation time.
- **Sequential Offloading:** Currently using `enable_model_cpu_offload`. While VRAM efficient, it adds latency. If scaling to a 24GB+ GPU, switch to **Pipeline Parallelism** for faster throughput.
- **Inference Batching:** Group multiple edit requests into a single GPU pass to maximize throughput during high-traffic forensic operations.
