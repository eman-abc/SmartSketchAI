import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# MOCKING SYSTEM DEPENDENCIES
# ---------------------------------------------------------------------------
# We mock heavy ML and Django libraries to allow running tests in any environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

# Mock heavy modules that are usually not in the local venv or require GPU
mock_modules = [
    "gfpgan",
    "facexlib",
    "basicsr",
]

# We also mock Django models/auth as they require a setup database
sys.modules["api.models"] = MagicMock()
sys.modules["django.contrib.auth.models"] = MagicMock()
sys.modules["django.db"] = MagicMock()

for mod_name in mock_modules:
    sys.modules[mod_name] = MagicMock()

# Add project root (backend-service) to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Try to get MemorySaver for tests
try:
    from langgraph.checkpoint.memory import MemorySaver
    TEST_CHECKPOINTER = MemorySaver()
except ImportError:
    TEST_CHECKPOINTER = None

# Patch the DjangoCheckpointer class before importing the agent
with patch('ml_engine.persistence.DjangoCheckpointer', MagicMock()):
    from ml_engine.agent_nodes import AnalyzerNode
    from ml_engine.agent_state import SuspectProfile, ForensicAgentState
    from ml_engine.agent import SmartSketchAgent
    from ml_engine.restorer import FaceRestorer


class TestForensicFeatures(unittest.TestCase):
    """
    Test suite for Advanced Forensic Restoration features.
    Verifies logic and payload structure without requiring full ML stack.
    """

    def setUp(self):
        # Mock LLM for AnalyzerNode
        self.mock_llm = MagicMock()
        self.analyzer = AnalyzerNode(llm=self.mock_llm)

    def test_analyzer_prompt_enhancement(self):
        """Verify that AnalyzerNode correctly extracts enhanced and negative prompts."""
        mock_response = MagicMock()
        mock_response.content = """
        {
            "intent": "generate",
            "enhanced_prompt": "highly detailed realistic forensic portrait of a middle-aged male, rugged complexion, sun-damaged skin",
            "negative_prompt": "beard, facial hair, glasses",
            "profile": {
                "gender": "male",
                "age_range": "45-55"
            }
        }
        """
        self.mock_llm.invoke.return_value = mock_response

        state: ForensicAgentState = {
            "messages": [{"role": "user", "content": "He has a rough face, no beard."}],
            "suspect_profile": SuspectProfile(),
            "iteration_count": 0,
            "user_intent": None,
            "enhanced_prompt": None,
            "negative_prompt": None
        }

        result = self.analyzer(state)

        self.assertEqual(result['user_intent'], "generate")
        self.assertIn("rugged complexion", result['enhanced_prompt'])
        self.assertIn("beard", result['negative_prompt'])
        print("[PASS] Analyzer correctly enhanced prompt and identified negative constraints.")

    def test_analyzer_age_intent(self):
        """Verify that AnalyzerNode correctly identifies 'age' intent and extracts parameters."""
        mock_response = MagicMock()
        mock_response.content = """
        {
            "intent": "age",
            "enhanced_prompt": "same person, now in their 50s, deep wrinkles, grey hair, weathered skin",
            "negative_prompt": "youthful skin, smooth face",
            "age_params": {"years": 20},
            "profile": {
                "age_range": "50-60"
            }
        }
        """
        self.mock_llm.invoke.return_value = mock_response

        state: ForensicAgentState = {
            "messages": [{"role": "user", "content": "How would he look in 20 years?"}],
            "suspect_profile": SuspectProfile(age_range="30-40"),
            "iteration_count": 0,
            "user_intent": None,
            "enhanced_prompt": None,
            "negative_prompt": None,
            "age_params": None
        }

        result = self.analyzer(state)

        self.assertEqual(result['user_intent'], "age")
        self.assertEqual(result['age_params']['years'], 20)
        self.assertIn("deep wrinkles", result['enhanced_prompt'])
        print("[PASS] Analyzer correctly identified 'age' intent and extracted relative years.")

    def test_artist_remote_payload(self):
        """Verify that ArtistNode passes the correct enhanced/negative prompts to Modal."""
        # Ensure we don't pass a MagicMock as a checkpointer to LangGraph
        agent = SmartSketchAgent(remote_url="http://mock-modal-service", checkpointer=TEST_CHECKPOINTER)

        state: ForensicAgentState = {
            "messages": [{"role": "user", "content": "test"}],
            "suspect_profile": SuspectProfile(gender="male"),
            "enhanced_prompt": "enhanced forensic description",
            "negative_prompt": "no glasses, no hat",
            "next_step": "generate",
            "generation_params": {}
        }

        with patch('requests.post') as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"success": True, "image_base64": "SGVsbG8="}
            mock_post.return_value = mock_resp

            agent._artist_node(state)

            # Check the JSON payload sent to the remote ML service
            args, kwargs = mock_post.call_args
            payload = kwargs['json']

            self.assertEqual(payload['prompt'], "enhanced forensic description")
            self.assertEqual(payload['negative_prompt'], "no glasses, no hat")
            print("[PASS] Artist node correctly transmitted enhanced prompts to remote service.")

    def test_face_restoration_logic(self):
        """Verify that the FaceRestorer correctly processes images."""
        with patch('ml_engine.restorer.GFPGANer') as mock_gfpgan_class:
            from PIL import Image
            import numpy as np

            # Setup mock restorer instance
            mock_instance = mock_gfpgan_class.return_value
            mock_instance.enhance.return_value = (None, None, np.zeros((512, 512, 3), dtype=np.uint8))

            restorer = FaceRestorer(model_path="dummy.pth", device="cpu")
            test_img = Image.new('RGB', (512, 512), color='red')
            
            restored_img = restorer.restore(test_img)
            
            self.assertIsInstance(restored_img, Image.Image)
            self.assertTrue(mock_instance.enhance.called)
            print("[PASS] FaceRestorer correctly wrapped GFPGAN enhancement logic.")


if __name__ == "__main__":
    unittest.main()
