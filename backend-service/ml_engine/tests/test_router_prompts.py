"""Tests for generation prompt assembly, negative sanitization, and router age rules."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ml_engine.agent_nodes import (
    RouterNode,
    build_initial_generation_prompt,
    sanitize_negative_prompt,
)
from ml_engine.agent_state import SuspectProfile


class SanitizeNegativeTests(unittest.TestCase):
    def test_drops_clauses_that_duplicate_profile(self):
        profile = SuspectProfile(
            gender="male",
            face_shape="square",
            hair_style="short",
            hair_color="brown",
            eye_color="brown",
        )
        profile_text = profile.to_detailed_prompt().lower()
        self.assertIn("square", profile_text)
        neg = "with square face shape, cartoon artifact"
        out = sanitize_negative_prompt(neg, profile)
        self.assertIsNotNone(out)
        self.assertNotIn("square face shape", out.lower())
        self.assertIn("cartoon", out.lower())

    def test_empty_returns_none(self):
        self.assertIsNone(sanitize_negative_prompt(None, SuspectProfile()))
        self.assertIsNone(sanitize_negative_prompt("   ", SuspectProfile()))


class BuildInitialPromptTests(unittest.TestCase):
    def test_combines_user_message_profile_and_enhanced(self):
        state = {
            "messages": [{"role": "user", "content": "Suspect from downtown robbery"}],
            "suspect_profile": SuspectProfile(gender="male", age_range="40-45"),
            "enhanced_prompt": "deep forehead wrinkles, tired eyes",
        }
        p = build_initial_generation_prompt(state)
        self.assertIn("downtown robbery", p)
        self.assertIn("male", p)
        self.assertIn("deep forehead wrinkles", p)
        self.assertIn("forensic photograph", p.lower())

    def test_skips_system_action_placeholder(self):
        state = {
            "messages": [{"role": "user", "content": "[system_action: regenerate]"}],
            "suspect_profile": SuspectProfile(gender="female"),
            "enhanced_prompt": None,
        }
        p = build_initial_generation_prompt(state)
        self.assertIn("female", p)
        self.assertNotIn("system_action", p)


class RouterAgeTests(unittest.TestCase):
    def setUp(self):
        self.router = RouterNode()

    def test_no_image_always_generate(self):
        state = {
            "messages": [{"role": "user", "content": "age him 20 years"}],
            "current_image": None,
            "user_intent": "edit",
            "age_params": {"years": 20},
        }
        r = self.router(state)
        self.assertEqual(r["next_step"], "generate")

    def test_explicit_age_intent_routes_age(self):
        state = {
            "messages": [{"role": "user", "content": "what would he look like in 10 years?"}],
            "current_image": "fakeb64",
            "user_intent": "age",
            "age_params": {"years": 10},
        }
        r = self.router(state)
        self.assertEqual(r["next_step"], "age")

    def test_edit_with_age_params_and_aging_language_routes_age(self):
        state = {
            "messages": [{"role": "user", "content": "Make him look 10 years older, same person"}],
            "current_image": "fakeb64",
            "user_intent": "edit",
            "age_params": {"years": 10},
        }
        r = self.router(state)
        self.assertEqual(r["next_step"], "age")

    def test_edit_scar_without_aging_language_not_age(self):
        state = {
            "messages": [{"role": "user", "content": "Add a scar on the right cheek"}],
            "current_image": "fakeb64",
            "user_intent": "edit",
            "age_params": {"years": 10},
        }
        r = self.router(state)
        self.assertNotEqual(r["next_step"], "age")
        self.assertIn(r["next_step"], ("edit", "inpaint"))


if __name__ == "__main__":
    unittest.main()
