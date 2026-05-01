import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient


def _parse_sse(raw_text):
    events = []
    for block in raw_text.strip().split("\n\n"):
        if not block.strip():
            continue
        event_name = None
        data_payload = None
        for line in block.splitlines():
            if line.startswith("event: "):
                event_name = line.replace("event: ", "", 1).strip()
            elif line.startswith("data: "):
                data_payload = json.loads(line.replace("data: ", "", 1))
        events.append({"event": event_name, "data": data_payload})
    return events


class AgentChatStreamTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            username="stream_tester",
            password="testpassword123",
            role="forensic",
        )
        self.client.force_authenticate(user=self.user)

    def test_stream_requires_message(self):
        response = self.client.post("/api/forensic/chat/stream/", {}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"], "message is required")

    def test_stream_emits_status_and_result_events(self):
        class DummyAgent:
            def run(self, message, thread_id):
                self.last_call = {"message": message, "thread_id": thread_id}
                return {
                    "suspect_profile": None,
                    "current_image": None,
                    "generation_id": "agent_stream_gen_001",
                    "generation_params": {"last_identity_score": 0.91},
                    "last_score": 89.5,
                    "is_verified": True,
                    "next_step": "refine",
                    "iteration_count": 2,
                    "last_error": None,
                    "verification_history": [],
                    "critic_report": None,
                }

        with patch("api.views.MLService.get_agent", return_value=DummyAgent()):
            response = self.client.post(
                "/api/forensic/chat/stream/",
                {"message": "Male suspect with blue eyes", "thread_id": "thread_stream_test"},
                format="json",
            )
            raw = ""
            for chunk in response.streaming_content:
                raw += chunk.decode("utf-8") if isinstance(chunk, bytes) else chunk

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/event-stream")
        self.assertEqual(response["Cache-Control"], "no-cache")

        events = _parse_sse(raw)
        self.assertGreaterEqual(len(events), 5)

        self.assertEqual(events[0]["event"], "status")
        self.assertIn("[Analyzer]", events[0]["data"]["message"])

        self.assertEqual(events[1]["event"], "status")
        self.assertIn("[Modal]", events[1]["data"]["message"])

        self.assertEqual(events[2]["event"], "progress")
        self.assertIn("[Artist]", events[2]["data"]["message"])

        result_event = events[-1]
        self.assertEqual(result_event["event"], "result")
        self.assertEqual(result_event["data"]["status"], "success")
        self.assertEqual(result_event["data"]["thread_id"], "thread_stream_test")
        self.assertEqual(result_event["data"]["generation_id"], "agent_stream_gen_001")

    def test_stream_requires_authentication(self):
        unauth_client = APIClient()
        response = unauth_client.post(
            "/api/forensic/chat/stream/",
            {"message": "unauthenticated"},
            format="json",
        )
        self.assertEqual(response.status_code, 401)
