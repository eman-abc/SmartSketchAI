"""
Self-hosted forensic vision critic utilities.

The Modal service hosts the vision-language model. Django and the LangGraph
agent use this lightweight client/parser so no Gemini or external API key is
required.
"""
import base64
import io
import json
import re
from typing import Any, Dict, Optional

import requests
from PIL import Image as PilImage


DEFAULT_CRITIC_REPORT: Dict[str, Any] = {
    "decision": "accept",
    "score": None,
    "issues": [],
    "matched_features": [],
    "missing_features": [],
    "prompt_adjustment": "",
    "safety_flags": [],
    "reasoning_summary": "Critic unavailable; accepted by fallback.",
    "model": "critic-fallback",
}


def normalize_critic_report(data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Return a stable critic report shape for API/UI/persistence use."""
    raw = data or {}
    report = dict(DEFAULT_CRITIC_REPORT)
    report.update({k: v for k, v in raw.items() if v is not None})

    decision = str(report.get("decision") or "accept").lower()
    report["decision"] = "revise" if decision in {"revise", "retry", "reject"} else "accept"

    for key in ("issues", "matched_features", "missing_features", "safety_flags"):
        value = report.get(key)
        if isinstance(value, str):
            report[key] = [value]
        elif not isinstance(value, list):
            report[key] = []

    try:
        report["score"] = None if report.get("score") is None else float(report["score"])
    except (TypeError, ValueError):
        report["score"] = None

    report["prompt_adjustment"] = str(report.get("prompt_adjustment") or "")
    report["reasoning_summary"] = str(report.get("reasoning_summary") or "")
    report["model"] = str(report.get("model") or "self-hosted-vlm")
    return report


def parse_critic_response(text: str) -> Dict[str, Any]:
    """Extract and normalize the JSON object returned by the VLM."""
    if not text:
        return normalize_critic_report(
            {"decision": "accept", "reasoning_summary": "Empty critic response."}
        )

    cleaned = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
    if fenced:
        cleaned = fenced.group(1)
    else:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            cleaned = match.group(0)

    try:
        return normalize_critic_report(json.loads(cleaned))
    except Exception:
        return normalize_critic_report(
            {
                "decision": "accept",
                "issues": ["critic_parse_error"],
                "reasoning_summary": "Critic response could not be parsed as JSON.",
            }
        )


def pil_to_b64(image: PilImage.Image) -> str:
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


class ForensicCriticClient:
    """HTTP client for the Modal-hosted VLM critic."""

    def __init__(self, remote_url: Optional[str], timeout: int = 90):
        self.remote_url = remote_url
        self.timeout = timeout

    def is_configured(self) -> bool:
        return bool(self.remote_url)

    def analyze(
        self,
        image: PilImage.Image,
        suspect_profile: Dict[str, Any],
        prompt: str,
        route_used: str,
        scores: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not self.remote_url:
            return normalize_critic_report(None)

        base = self.remote_url.rstrip("/")
        for suffix in ("/generate", "/edit", "/age", "/analyze", "/critic"):
            if base.endswith(suffix):
                base = base.rsplit("/", 1)[0]

        try:
            resp = requests.post(
                f"{base}/critic",
                json={
                    "image_base64": pil_to_b64(image),
                    "suspect_profile": suspect_profile,
                    "prompt": prompt,
                    "route_used": route_used,
                    "scores": scores or {},
                    "metadata": metadata or {},
                },
                timeout=self.timeout,
            )
            if resp.status_code != 200:
                return normalize_critic_report(
                    {
                        "decision": "accept",
                        "issues": [f"critic_http_{resp.status_code}"],
                        "reasoning_summary": "Critic service returned a non-200 response.",
                    }
                )
            data = resp.json()
            if data.get("success") and data.get("critic_report"):
                return normalize_critic_report(data["critic_report"])
            return normalize_critic_report(data)
        except Exception as exc:
            return normalize_critic_report(
                {
                    "decision": "accept",
                    "issues": ["critic_request_failed"],
                    "reasoning_summary": f"Critic request failed: {exc}",
                }
            )
