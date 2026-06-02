"""Minimal standalone `openminion-eval` quickstart example."""

from __future__ import annotations

import json

from openminion_eval import EvalRunner, EvalSuite
from openminion_eval.schemas import EvalTranscript


def run_quickstart() -> dict[str, object]:
    transcript = EvalTranscript(
        name="hello-world",
        turns=[{"user": "ping", "expected": "pong"}],
        tags=["quickstart"],
    )
    suite = EvalSuite(
        runner=EvalRunner(agent_executor=lambda _user_input: "pong"),
        threshold=1.0,
    )
    result = suite.run([transcript], scorer_name="exact_match")
    summary = result.summaries[0]

    return {
        "total_transcripts": result.total_transcripts,
        "failed_transcripts": result.failed_transcripts,
        "summary_name": summary.transcript_name,
        "total_turns": summary.total_turns,
    }


def main() -> int:
    print(json.dumps(run_quickstart(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
