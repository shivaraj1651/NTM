"""
Shared eval infrastructure: ScoreCard, scoring helpers, Haiku mock, --live marker, JSON reporter.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

GOLDEN_DIR = Path(__file__).parents[3] / "docs" / "golden"
EVALS_DIR = Path(__file__).parents[3] / "docs" / "evals"
PASS_THRESHOLD = 80.0
HAIKU_MODEL = "claude-haiku-4-5-20251001"


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class ScoreCard:
    agent_id: str
    agent_name: str
    mandate_id: str
    completeness: float
    format_score: float
    coherence: Optional[float] = None
    overall: float = field(init=False)

    def __post_init__(self) -> None:
        if self.coherence is not None:
            self.overall = 0.4 * self.completeness + 0.3 * self.format_score + 0.3 * self.coherence
        else:
            self.overall = 0.5 * self.completeness + 0.5 * self.format_score

    @property
    def passed(self) -> bool:
        return self.overall >= PASS_THRESHOLD


# ---------------------------------------------------------------------------
# Golden fixture loader
# ---------------------------------------------------------------------------

def load_golden(mandate_id: str) -> Dict[str, Any]:
    """Load docs/golden/mandate_N_concept.json."""
    path = GOLDEN_DIR / f"{mandate_id}_concept.json"
    with open(path) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------

def score_completeness(output: Any, required_fields: List[str]) -> float:
    """Count required top-level keys present in output dict (0-100)."""
    if not isinstance(output, dict):
        return 0.0
    present = sum(1 for f in required_fields if f in output and output[f] is not None)
    return round(present / len(required_fields) * 100, 1) if required_fields else 100.0


def score_format(output: Any, required_types: Dict[str, type]) -> float:
    """Binary: 100 if all required keys exist at correct type, 0 otherwise."""
    if not isinstance(output, dict):
        return 0.0
    for key, expected_type in required_types.items():
        if key not in output:
            return 0.0
        if not isinstance(output[key], expected_type):
            return 0.0
    return 100.0


async def score_coherence(
    agent_output: Dict[str, Any],
    golden_output: Dict[str, Any],
    client,
) -> float:
    """Call Haiku to judge coherence of agent output vs golden reference (0-100)."""
    prompt = (
        f"Golden reference:\n{json.dumps(golden_output, indent=2)}\n\n"
        f"Agent output:\n{json.dumps(agent_output, indent=2)}\n\n"
        "Rate the coherence and completeness of the agent output compared to the "
        "golden reference on a scale of 0-100. Focus on strategic alignment, "
        "required fields, and output quality. "
        'Return ONLY valid JSON: {"score": <integer>}'
    )
    response = await client.messages.create(
        model=HAIKU_MODEL,
        max_tokens=100,
        messages=[{"role": "user", "content": prompt}],
    )
    try:
        result = json.loads(response.content[0].text)
        return float(result["score"])
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        return 0.0


# ---------------------------------------------------------------------------
# pytest marker + fixtures
# ---------------------------------------------------------------------------

def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "live: make real Anthropic API calls for agent execution and coherence scoring",
    )


@pytest.fixture(autouse=True)
def mock_agent_llm(request):
    """
    Patch anthropic.AsyncAnthropic for all eval tests unless -m live is active.
    Returns a mock client whose messages.create returns a configurable response.
    """
    if request.node.get_closest_marker("live"):
        yield None
        return

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='{"score": 85}')]
    mock_client.messages.create = AsyncMock(return_value=mock_response)

    with patch("anthropic.AsyncAnthropic", return_value=mock_client):
        yield mock_client


@pytest.fixture(scope="session")
def eval_results() -> List[ScoreCard]:
    """Session-scoped accumulator for ScoreCard results."""
    return []


@pytest.fixture(scope="session", autouse=True)
def json_reporter(eval_results, request):
    """Write JSON report + print console table after session ends."""
    yield  # run all tests first

    if not eval_results:
        return

    is_live = any(
        item.get_closest_marker("live")
        for item in request.session.items
    )
    mode = "live" if is_live else "mock"

    # Group by agent
    agents_seen: Dict[str, List[ScoreCard]] = {}
    for sc in eval_results:
        agents_seen.setdefault(sc.agent_id, []).append(sc)

    agent_summaries = []
    all_pass = True
    for agent_id, cards in sorted(agents_seen.items()):
        avg_completeness = sum(c.completeness for c in cards) / len(cards)
        avg_format = sum(c.format_score for c in cards) / len(cards)
        coherence_vals = [c.coherence for c in cards if c.coherence is not None]
        avg_coherence = sum(coherence_vals) / len(coherence_vals) if coherence_vals else None
        avg_overall = sum(c.overall for c in cards) / len(cards)
        passed = avg_overall >= PASS_THRESHOLD

        if not passed:
            all_pass = False

        agent_summaries.append({
            "id": agent_id,
            "name": cards[0].agent_name,
            "completeness": round(avg_completeness, 1),
            "format": round(avg_format, 1),
            "coherence": round(avg_coherence, 1) if avg_coherence is not None else None,
            "overall": round(avg_overall, 1),
            "pass": passed,
            "mandates_tested": len(cards),
        })

    report = {
        "run_date": date.today().isoformat(),
        "mode": mode,
        "threshold": PASS_THRESHOLD,
        "overall_pass": all_pass,
        "agents": agent_summaries,
    }

    # Write JSON
    EVALS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = EVALS_DIR / f"results_{date.today().isoformat()}.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    # Print console table
    print("\n")
    print(f"NTM Agent Eval Results  {date.today().isoformat()}  [mode: {mode}]")
    print("─" * 62)
    print(f"{'Agent':<8} {'completeness':>13} {'format':>7} {'coherence':>10} {'overall':>8}")
    for a in agent_summaries:
        coh = f"{a['coherence']:.1f}" if a["coherence"] is not None else "—"
        mark = "✓" if a["pass"] else "✗"
        print(
            f"{a['id']:<8} {a['completeness']:>13.1f} {a['format']:>7.1f} "
            f"{coh:>10} {a['overall']:>7.1f} {mark}"
        )
    print("─" * 62)
    total = len(agent_summaries)
    passed = sum(1 for a in agent_summaries if a["pass"])
    verdict = "PASS" if all_pass else "FAIL"
    print(f"Overall: {verdict}  {passed}/{total} agents ≥ {PASS_THRESHOLD}")
    print(f"Report saved: {report_path}\n")
