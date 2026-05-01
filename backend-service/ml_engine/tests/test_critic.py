import unittest
from unittest.mock import MagicMock

from PIL import Image

from ml_engine.agent_nodes import VerificationNode
from ml_engine.agent_state import SuspectProfile
from ml_engine.critic import parse_critic_response


class CriticParserTests(unittest.TestCase):
    def test_parse_valid_json(self):
        report = parse_critic_response(
            '{"decision":"revise","score":42,"issues":["eyes"],'
            '"prompt_adjustment":"make eyes darker","reasoning_summary":"Eyes mismatch."}'
        )
        self.assertEqual(report["decision"], "revise")
        self.assertEqual(report["score"], 42.0)
        self.assertEqual(report["prompt_adjustment"], "make eyes darker")

    def test_parse_fenced_json(self):
        report = parse_critic_response(
            '```json\n{"decision":"accept","score":88,"reasoning_summary":"Matches."}\n```'
        )
        self.assertEqual(report["decision"], "accept")
        self.assertEqual(report["score"], 88.0)

    def test_parse_malformed_text_falls_back(self):
        report = parse_critic_response("not json")
        self.assertEqual(report["decision"], "accept")
        self.assertIn("critic_parse_error", report["issues"])


class VerificationCriticTests(unittest.TestCase):
    def test_verifier_retries_with_critic_adjustment(self):
        critic_client = MagicMock()
        critic_client.is_configured.return_value = True
        critic_client.analyze.return_value = {
            "decision": "revise",
            "score": 45,
            "issues": ["missing glasses"],
            "matched_features": [],
            "missing_features": ["round glasses"],
            "prompt_adjustment": "add clear round glasses while preserving identity",
            "safety_flags": [],
            "reasoning_summary": "Glasses are missing.",
            "model": "test-vlm",
        }

        verifier = VerificationNode(scorer=None, critic_client=critic_client)
        image = Image.new("RGB", (64, 64), "white")
        state = {
            "current_image": image,
            "iteration_count": 1,
            "suspect_profile": SuspectProfile(gender="male"),
            "generation_params": {},
            "next_step": "generate",
            "enhanced_prompt": "male suspect with round glasses",
            "critic_attempts": 0,
            "verification_history": [],
        }

        result = verifier(state)

        self.assertEqual(result["next_step"], "retry")
        self.assertFalse(result["is_verified"])
        self.assertIn("round glasses", result["critic_adjustment_prompt"])
        self.assertEqual(result["critic_attempts"], 1)

    def test_verifier_accepts_when_critic_accepts(self):
        critic_client = MagicMock()
        critic_client.is_configured.return_value = True
        critic_client.analyze.return_value = {
            "decision": "accept",
            "score": 91,
            "reasoning_summary": "Profile matches.",
        }

        verifier = VerificationNode(scorer=None, critic_client=critic_client)
        result = verifier(
            {
                "current_image": Image.new("RGB", (64, 64), "white"),
                "iteration_count": 1,
                "suspect_profile": SuspectProfile(),
                "generation_params": {},
                "next_step": "generate",
                "critic_attempts": 0,
            }
        )

        self.assertEqual(result["next_step"], "end")
        self.assertTrue(result["is_verified"])
        self.assertEqual(result["critic_report"]["decision"], "accept")


if __name__ == "__main__":
    unittest.main()
