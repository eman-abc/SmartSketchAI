"""
SmartSketch.AI - ML Engine Package

IMPORTANT — Lazy Import Policy
================================
This package is imported by the Django process on Render (CPU-only).
Heavy dependencies (torch, diffusers, transformers, clip, facenet, mediapipe)
must NEVER be imported at module load time here.

All GPU-heavy work runs exclusively on the remote Modal ML service.
Django only imports lightweight agent/state/persistence modules.
"""

# ---------------------------------------------------------------------------
# Mediapipe compatibility shim
# Applied lazily when the masker module is actually used by the remote ML service.
# We still register the shim here so imports inside masker.py don't fail
# on environments where mediapipe is absent or partially installed.
# ---------------------------------------------------------------------------
import sys as _sys
from unittest.mock import MagicMock as _MagicMock

try:
    import mediapipe as _mp
    if not hasattr(_mp, "solutions"):
        _mp.solutions = _MagicMock()
except ImportError:
    _mock_mp = _MagicMock()
    _sys.modules.setdefault("mediapipe", _mock_mp)
    _sys.modules.setdefault("mediapipe.solutions", _MagicMock())
    _sys.modules.setdefault("mediapipe.solutions.face_mesh", _MagicMock())
    _sys.modules.setdefault("mediapipe.solutions.drawing_utils", _MagicMock())
    _sys.modules.setdefault("mediapipe.solutions.drawing_styles", _MagicMock())

# ---------------------------------------------------------------------------
# Package metadata
# ---------------------------------------------------------------------------
__version__     = "1.3.0"
__author__      = "Muqaddas Anees, Muqadas Zahra, Eman Chaudhary"
__institution__ = "NUST SEECS"

# ---------------------------------------------------------------------------
# NO eager heavy imports below this line.
# Use explicit imports in the modules that need them (generator.py, etc.).
#
# Allowed lazy __all__ so tools like IDEs can still discover the public API
# without triggering model downloads or CUDA initialisation.
# ---------------------------------------------------------------------------
__all__ = [
    "ForensicPromptValidator",
    "FaceGenerator",
    "FaceScorer",
    "MemoryEfficientSketchConverter",
    "FaceEditor",
    "FaceInpainter",
    "SmartSketchPipeline",
    "SmartSketchAgent",
    "ForensicAgentState",
    "SuspectProfile",
    # Lightweight modules safe to import anywhere
    "DjangoCheckpointer",
]