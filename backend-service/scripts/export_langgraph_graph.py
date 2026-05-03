#!/usr/bin/env python3
"""
Export the SmartSketch LangGraph structure to Mermaid (and optional PNG).

Run from repository root:
  python backend-service/scripts/export_langgraph_graph.py

Or from backend-service:
  python scripts/export_langgraph_graph.py

Requires Django setup because ml_engine imports the Django checkpointer module;
uses MemorySaver so no DB reads/writes occur.
"""
from __future__ import annotations

import argparse
import os
import sys


def _backend_dir() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def main() -> int:
    parser = argparse.ArgumentParser(description="Export SmartSketchAgent LangGraph to Mermaid/PNG.")
    parser.add_argument(
        "-o",
        "--output",
        default="",
        help="Output path for .mmd (default: backend-service/ml_engine/smartsketch_agent_graph.mmd)",
    )
    parser.add_argument(
        "--png",
        default="",
        help="If set, also write PNG to this path (requires graphviz/pygraphviz).",
    )
    args = parser.parse_args()

    backend = _backend_dir()
    if backend not in sys.path:
        sys.path.insert(0, backend)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smartsketch_backend.settings")
    import django

    django.setup()

    from langgraph.checkpoint.memory import MemorySaver

    from ml_engine.agent import SmartSketchAgent

    agent = SmartSketchAgent(checkpointer=MemorySaver())
    graph = agent.app.get_graph()

    mermaid = graph.draw_mermaid()
    # When several conditional branches share the same target node, LangGraph's Mermaid
    # export may show only one edge label. Document the real router keys from agent.py.
    legend = (
        "%% SmartSketch LangGraph (ForensicAgentState)\n"
        "%% Route → artist runs for next_step in: generate | edit | inpaint | age\n"
        "%% (Mermaid may show a single combined edge to `artist` when targets coincide.)\n"
        "%% Verify → artist on retry; verify → __end__ on end.\n\n"
    )
    out = args.output or os.path.join(backend, "ml_engine", "smartsketch_agent_graph.mmd")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(legend + mermaid)
    print(f"Wrote Mermaid: {out}")

    if args.png:
        try:
            png_bytes = graph.draw_mermaid_png()
        except Exception as e:
            print(f"PNG export failed ({e}). Install graphviz and ensure it is on PATH.", file=sys.stderr)
            return 1
        os.makedirs(os.path.dirname(os.path.abspath(args.png)) or ".", exist_ok=True)
        with open(args.png, "wb") as f:
            f.write(png_bytes)
        print(f"Wrote PNG: {args.png}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
