from pathlib import Path
import unittest


class ModalConfigTests(unittest.TestCase):
    def test_modal_uses_l4_default_and_critic_service(self):
        modal_app = Path(__file__).resolve().parents[2] / "ml_service" / "modal_app.py"
        source = modal_app.read_text(encoding="utf-8")

        self.assertIn('os.environ.get("MODAL_GPU", "L4")', source)
        self.assertIn("class ForensicCriticService", source)
        self.assertIn('@web_app.post("/critic")', source)


    def test_modal_cleanup_is_applied_to_gpu_endpoints(self):
        modal_app = Path(__file__).resolve().parents[2] / "ml_service" / "modal_app.py"
        source = modal_app.read_text(encoding="utf-8")

        self.assertIn("def _cleanup_cuda", source)
        self.assertGreaterEqual(source.count("_cleanup_cuda()"), 5)


if __name__ == "__main__":
    unittest.main()
