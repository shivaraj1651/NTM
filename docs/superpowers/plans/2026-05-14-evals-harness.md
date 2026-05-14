# Agent Eval Harness Implementation Plan (TASK-029)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a repeatable eval harness for AGT-01 through AGT-05 that scores each agent on completeness, format, and coherence (AGT-03 only), asserts ≥ 80 overall, and outputs a console table + JSON report.

**Architecture:** One pytest file per agent in `backend/tests/agents/`. Shared `conftest_evals.py` owns the Haiku mock, `--live` marker, `ScoreCard` dataclass, and JSON reporter. Golden reference fixtures are hardcoded JSONs in `docs/golden/`. Fast mode mocks all LLM calls; `--live` runs real API calls.

**Tech Stack:** pytest, pytest-asyncio, unittest.mock, anthropic (Haiku for coherence), Python dataclasses, json

---

## File Map

| File | Action |
|---|---|
| `docs/golden/mandate_1_concept.json` | Create |
| `docs/golden/mandate_2_concept.json` | Create |
| `docs/golden/mandate_3_concept.json` | Create |
| `docs/evals/.gitkeep` | Create |
| `backend/tests/agents/conftest_evals.py` | Create |
| `backend/tests/agents/test_eval_agt01.py` | Create |
| `backend/tests/agents/test_eval_agt02.py` | Create |
| `backend/tests/agents/test_eval_agt03.py` | Create |
| `backend/tests/agents/test_eval_agt04.py` | Create |
| `backend/tests/agents/test_eval_agt05.py` | Create |

---

### Task 1: Seed golden fixtures and evals directory

**Files:**
- Create: `docs/golden/mandate_1_concept.json`
- Create: `docs/golden/mandate_2_concept.json`
- Create: `docs/golden/mandate_3_concept.json`
- Create: `docs/evals/.gitkeep`

- [ ] **Step 1: Create mandate_1_concept.json** (Consumer FMCG, Southeast Asia, $500K)

```json
{
  "mandate_id": "mandate_1",
  "campaign_name": "Summer Refresh 2026",
  "input_mandate": {
    "approval_date": "2026-05-01",
    "mandated_by": "cmo",
    "version": "1.0",
    "status": "approved",
    "campaign_concept": {
      "id": "cc-001",
      "name": "Summer Refresh 2026",
      "objective": "Increase brand awareness among 18-45 urban demographic by 25%",
      "description": "Q2 multichannel campaign targeting urban professionals across Southeast Asia",
      "target_audience": "18-45 urban professionals, mobile-first, health-conscious",
      "timeline": "June-July 2026 (8 weeks)"
    },
    "budget": {
      "total_amount": 500000,
      "currency": "USD",
      "allocation_strategy": "60% digital, 40% offline",
      "contingency_reserve": "10%"
    },
    "geography": {
      "regions": ["Southeast Asia"],
      "markets": ["SG", "MY", "TH"],
      "country_list": ["SG", "MY", "TH"]
    }
  },
  "golden_outputs": {
    "agt01_validation": {
      "is_valid": true,
      "completeness_score": 100,
      "missing_fields": []
    },
    "agt02_competitors": [
      {"name": "Unilever", "confidence": 90},
      {"name": "P&G", "confidence": 88},
      {"name": "Nestle", "confidence": 75},
      {"name": "Colgate-Palmolive", "confidence": 70},
      {"name": "Reckitt", "confidence": 65}
    ],
    "agt03_concept": {
      "name": "Refresh Your City",
      "tagline": "Where urban life meets natural energy",
      "strategic_narrative": "Competitors focus on price; we own the health-and-vitality space in SEA urban markets.",
      "campaign_theme": "Urban Vitality",
      "audience_segmentation": {
        "primary": "Urban professionals 25-35, Singapore and KL",
        "secondary": "Health-conscious millennials 18-24",
        "tertiary": "Aspirational Gen-X 36-45"
      },
      "channel_mix": [
        {"channel": "Instagram", "rationale": "Primary audience native platform", "competitor_gap": "Competitors use generic creative"},
        {"channel": "TikTok", "rationale": "High engagement with 18-30 segment", "competitor_gap": "Category largely absent"},
        {"channel": "OOH", "rationale": "Urban commuter touchpoints", "competitor_gap": "Digital competitors ignore offline"}
      ],
      "message_architecture": {
        "master_message": "Refresh your city, refresh yourself",
        "channel_adaptations": {
          "Instagram": "Lifestyle imagery with urban backdrops",
          "TikTok": "15-second refresh challenge format",
          "OOH": "Bold visual, single CTA"
        }
      },
      "campaign_phasing": {
        "awareness": "Weeks 1-2: Influencer seeding + OOH launch",
        "engagement": "Weeks 3-6: UGC challenge + Instagram carousel series",
        "conversion": "Weeks 7-8: Promo codes + limited edition pack push"
      },
      "tone_board": {
        "adjectives": ["fresh", "vibrant", "urban", "confident", "authentic"],
        "visual_direction": "Bright greens and whites, clean typography, candid urban photography"
      },
      "mandate_fit_score": 9,
      "gap_exploitation_score": 8
    }
  }
}
```

- [ ] **Step 2: Create mandate_2_concept.json** (B2B SaaS, North America, $200K)

```json
{
  "mandate_id": "mandate_2",
  "campaign_name": "Enterprise AI Launch 2026",
  "input_mandate": {
    "approval_date": "2026-05-01",
    "mandated_by": "vp_marketing",
    "version": "1.0",
    "status": "approved",
    "campaign_concept": {
      "id": "cc-002",
      "name": "Enterprise AI Launch 2026",
      "objective": "Generate 500 qualified enterprise leads for AI platform in Q3 2026",
      "description": "B2B demand generation campaign targeting enterprise IT decision-makers",
      "target_audience": "CTO, CIO, VP Engineering at companies 500+ employees",
      "timeline": "July-September 2026 (12 weeks)"
    },
    "budget": {
      "total_amount": 200000,
      "currency": "USD",
      "allocation_strategy": "80% digital, 20% events",
      "contingency_reserve": "15%"
    },
    "geography": {
      "regions": ["North America"],
      "markets": ["US", "CA"],
      "country_list": ["US", "CA"]
    }
  },
  "golden_outputs": {
    "agt01_validation": {
      "is_valid": true,
      "completeness_score": 100,
      "missing_fields": []
    },
    "agt02_competitors": [
      {"name": "Salesforce", "confidence": 85},
      {"name": "Microsoft Azure AI", "confidence": 82},
      {"name": "Google Cloud AI", "confidence": 80},
      {"name": "IBM Watson", "confidence": 72},
      {"name": "ServiceNow", "confidence": 68}
    ],
    "agt03_concept": {
      "name": "The AI Advantage",
      "tagline": "Enterprise intelligence, delivered",
      "strategic_narrative": "Hyperscalers win on scale; we win on enterprise-grade reliability and white-glove onboarding.",
      "campaign_theme": "Trusted Enterprise AI",
      "audience_segmentation": {
        "primary": "CTOs and CIOs at 500-5000 employee companies",
        "secondary": "VP Engineering and IT Directors",
        "tertiary": "Enterprise architects and AI leads"
      },
      "channel_mix": [
        {"channel": "LinkedIn", "rationale": "Primary B2B decision-maker platform", "competitor_gap": "Competitors use generic awareness ads"},
        {"channel": "Google Search", "rationale": "High-intent enterprise search traffic", "competitor_gap": "Competitors underbid on long-tail enterprise terms"},
        {"channel": "Webinars", "rationale": "Thought leadership and demo pipeline", "competitor_gap": "Competitors lack hands-on demo content"}
      ],
      "message_architecture": {
        "master_message": "Your enterprise deserves AI that works",
        "channel_adaptations": {
          "LinkedIn": "ROI-focused case study format",
          "Google Search": "Problem-solution copy with CTA",
          "Webinars": "Deep-dive technical showcase"
        }
      },
      "campaign_phasing": {
        "awareness": "Weeks 1-4: Thought leadership content + LinkedIn ABM",
        "engagement": "Weeks 5-8: Webinar series + search retargeting",
        "conversion": "Weeks 9-12: Free trial offers + sales handoff"
      },
      "tone_board": {
        "adjectives": ["authoritative", "precise", "trustworthy", "innovative", "results-driven"],
        "visual_direction": "Deep navy and white, data visualization aesthetics, executive photography"
      },
      "mandate_fit_score": 9,
      "gap_exploitation_score": 7
    }
  }
}
```

- [ ] **Step 3: Create mandate_3_concept.json** (Luxury fashion, Europe, $1M)

```json
{
  "mandate_id": "mandate_3",
  "campaign_name": "Maison Autumn 2026",
  "input_mandate": {
    "approval_date": "2026-05-01",
    "mandated_by": "brand_director",
    "version": "1.0",
    "status": "approved",
    "campaign_concept": {
      "id": "cc-003",
      "name": "Maison Autumn 2026",
      "objective": "Drive consideration and purchase intent for autumn collection among HNW consumers",
      "description": "Premium brand campaign for autumn collection launch across European luxury markets",
      "target_audience": "HNW individuals 30-55, luxury fashion buyers, Paris/Milan/London",
      "timeline": "September-October 2026 (8 weeks)"
    },
    "budget": {
      "total_amount": 1000000,
      "currency": "EUR",
      "allocation_strategy": "50% digital, 30% print, 20% events",
      "contingency_reserve": "10%"
    },
    "geography": {
      "regions": ["Western Europe"],
      "markets": ["FR", "IT", "GB"],
      "country_list": ["FR", "IT", "GB"]
    }
  },
  "golden_outputs": {
    "agt01_validation": {
      "is_valid": true,
      "completeness_score": 100,
      "missing_fields": []
    },
    "agt02_competitors": [
      {"name": "LVMH", "confidence": 92},
      {"name": "Kering", "confidence": 88},
      {"name": "Richemont", "confidence": 82},
      {"name": "Burberry", "confidence": 78},
      {"name": "Prada Group", "confidence": 75}
    ],
    "agt03_concept": {
      "name": "L'Automne Éternel",
      "tagline": "Crafted for those who define the season",
      "strategic_narrative": "Mass luxury brands chase virality; we reclaim exclusivity through scarcity and editorial gravitas.",
      "campaign_theme": "Timeless Exclusivity",
      "audience_segmentation": {
        "primary": "HNW women 35-50, Paris and London fashion insiders",
        "secondary": "Affluent professional women 30-40",
        "tertiary": "Luxury fashion enthusiasts 25-30 aspirational tier"
      },
      "channel_mix": [
        {"channel": "Instagram", "rationale": "Visual storytelling for fashion audience", "competitor_gap": "Competitors over-post; we curate fewer, higher-quality moments"},
        {"channel": "Print", "rationale": "Vogue Paris/IT/UK for HNW print readers", "competitor_gap": "Competitors shifting to digital; we dominate premium print"},
        {"channel": "Events", "rationale": "Exclusive preview events for top-tier clientele", "competitor_gap": "Competitors scale events; we restrict access"}
      ],
      "message_architecture": {
        "master_message": "Autumn, as it was always meant to be worn",
        "channel_adaptations": {
          "Instagram": "Editorial campaign imagery, no product tags",
          "Print": "Full-page spread, minimal copy",
          "Events": "Private viewing, invitation only"
        }
      },
      "campaign_phasing": {
        "awareness": "Weeks 1-2: Press and editor preview + print placement",
        "engagement": "Weeks 3-6: Instagram editorial series + event invitations",
        "conversion": "Weeks 7-8: Private sale access + personal stylist CTA"
      },
      "tone_board": {
        "adjectives": ["refined", "exclusive", "timeless", "confident", "effortless"],
        "visual_direction": "Rich amber and charcoal palette, film photography aesthetic, serif typography"
      },
      "mandate_fit_score": 10,
      "gap_exploitation_score": 9
    }
  }
}
```

- [ ] **Step 4: Create docs/evals/.gitkeep**

Create an empty file at `docs/evals/.gitkeep`.

- [ ] **Step 5: Add docs/evals/*.json to .gitignore**

Open `.gitignore` at project root and add:
```
docs/evals/*.json
```

- [ ] **Step 6: Commit**

```bash
git add docs/golden/ docs/evals/.gitkeep .gitignore
git commit -m "feat(evals): seed 3 golden fixtures and evals output directory

Co-authored-by: katharguppe <katharguppe@users.noreply.github.com>"
```

---

### Task 2: Create conftest_evals.py

**Files:**
- Create: `backend/tests/agents/conftest_evals.py`

- [ ] **Step 1: Write the failing test** (verify conftest loads correctly)

Add a temporary test to `backend/tests/agents/conftest_evals.py` to confirm imports work. Skip this step if conftest files are not directly runnable — proceed straight to Step 2.

- [ ] **Step 2: Create conftest_evals.py**

```python
"""
Shared eval infrastructure: ScoreCard, scoring helpers, Haiku mock, --live marker, JSON reporter.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

GOLDEN_DIR = Path(__file__).parents[3] / "docs" / "golden"
EVALS_DIR = Path(__file__).parents[3] / "docs" / "evals"
PASS_THRESHOLD = 80.0


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
        model="claude-haiku-4-5-20251001",
        max_tokens=100,
        messages=[{"role": "user", "content": prompt}],
    )
    result = json.loads(response.content[0].text)
    return float(result["score"])


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
```

- [ ] **Step 3: Verify it imports without errors**

```bash
cd D:/staging/ntm
python -c "import backend.tests.agents.conftest_evals"
```

Expected: no output (no errors).

- [ ] **Step 4: Commit**

```bash
git add backend/tests/agents/conftest_evals.py
git commit -m "feat(evals): add shared conftest_evals.py with ScoreCard, scoring helpers, mock, reporter

Co-authored-by: katharguppe <katharguppe@users.noreply.github.com>"
```

---

### Task 3: test_eval_agt01.py — MandateAnalyst evals

**Files:**
- Create: `backend/tests/agents/test_eval_agt01.py`

AGT-01 entry point: `mandate_analyst_agent(mandate: Dict) -> Dict`
Expected output keys: `completeness_score` (int), `missing_fields` (list), `contradictions` (list), `mandate_summary` (dict), `validated_at` (str)
Scoring: completeness + format only (no coherence).

- [ ] **Step 1: Write the failing tests**

```python
"""Eval tests for AGT-01 MandateAnalyst."""
import pytest
from backend.app.agents.mandate_analyst import mandate_analyst_agent
from backend.tests.agents.conftest_evals import (
    ScoreCard, load_golden, score_completeness, score_format, PASS_THRESHOLD
)

REQUIRED_OUTPUT_FIELDS = [
    "completeness_score", "missing_fields", "contradictions", "mandate_summary", "validated_at"
]
REQUIRED_TYPES = {
    "completeness_score": (int, float),
    "missing_fields": list,
    "contradictions": list,
    "mandate_summary": dict,
    "validated_at": str,
}
MANDATE_IDS = ["mandate_1", "mandate_2", "mandate_3"]


@pytest.mark.parametrize("mandate_id", MANDATE_IDS)
@pytest.mark.asyncio
async def test_agt01_eval(mandate_id, eval_results, mock_agent_llm):
    """AGT-01 scores completeness + format ≥ 80 on each golden mandate."""
    golden = load_golden(mandate_id)
    mandate = golden["input_mandate"]

    # Configure mock to return realistic AGT-01 output
    if mock_agent_llm is not None:
        import json
        from unittest.mock import MagicMock
        llm_response = {
            "contradictions": [],
            "mandate_summary": {
                "objective": mandate["campaign_concept"]["objective"],
                "budget_total": f"{mandate['budget']['total_amount']} {mandate['budget']['currency']}",
                "timeline": mandate["campaign_concept"]["timeline"],
                "key_risks": [],
                "readiness": "Ready to proceed"
            },
            "completeness_score": 95
        }
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(llm_response))]
        mock_agent_llm.messages.create.return_value = mock_response

    output = await mandate_analyst_agent(mandate)

    completeness = score_completeness(output, REQUIRED_OUTPUT_FIELDS)
    fmt = score_format(output, REQUIRED_TYPES)

    card = ScoreCard(
        agent_id="AGT-01",
        agent_name="MandateAnalyst",
        mandate_id=mandate_id,
        completeness=completeness,
        format_score=fmt,
    )
    eval_results.append(card)

    assert card.overall >= PASS_THRESHOLD, (
        f"AGT-01 on {mandate_id}: overall={card.overall:.1f} "
        f"(completeness={completeness}, format={fmt})"
    )
```

- [ ] **Step 2: Run tests to verify they fail without implementation**

```bash
cd D:/staging/ntm
$env:PYTHONPATH = "."
pytest backend/tests/agents/test_eval_agt01.py -v --no-header 2>&1 | Select-Object -Last 20
```

Expected: tests are collected (3 parametrized cases). If `mandate_analyst_agent` is already implemented, they may pass — that is fine; verify no import errors.

- [ ] **Step 3: Run tests to verify they pass**

```bash
$env:PYTHONPATH = "."
pytest backend/tests/agents/test_eval_agt01.py -v --no-header -p no:warnings
```

Expected: `3 passed`.

- [ ] **Step 4: Commit**

```bash
git add backend/tests/agents/test_eval_agt01.py
git commit -m "feat(evals): add AGT-01 MandateAnalyst eval tests

Co-authored-by: katharguppe <katharguppe@users.noreply.github.com>"
```

---

### Task 4: test_eval_agt02.py — CompetitiveIntel evals

**Files:**
- Create: `backend/tests/agents/test_eval_agt02.py`

AGT-02 entry point: `identify_competitors_sync(mandate: Dict, client_profile: Dict) -> List[CompetitorIdentity]`
Output is a list of objects with `.name` (str) and `.confidence` (int).
Scoring: completeness (≥5 competitors returned, all have name+confidence) + format (all items parseable).

- [ ] **Step 1: Create test_eval_agt02.py**

```python
"""Eval tests for AGT-02 CompetitiveIntel."""
import pytest
from backend.app.agents.competitive_intel import identify_competitors_sync
from backend.tests.agents.conftest_evals import (
    ScoreCard, load_golden, PASS_THRESHOLD
)

MANDATE_IDS = ["mandate_1", "mandate_2", "mandate_3"]
MIN_COMPETITORS = 5


def _score_completeness_agt02(competitors) -> float:
    """Score: enough competitors returned + all have name and confidence."""
    if not competitors or len(competitors) < MIN_COMPETITORS:
        return 0.0
    valid = sum(
        1 for c in competitors
        if hasattr(c, "name") and c.name
        and hasattr(c, "confidence") and isinstance(c.confidence, int)
    )
    return round(valid / len(competitors) * 100, 1)


def _score_format_agt02(competitors) -> float:
    """Binary: all items have name (str) and confidence (int 0-100)."""
    if not competitors:
        return 0.0
    for c in competitors:
        if not hasattr(c, "name") or not isinstance(c.name, str):
            return 0.0
        if not hasattr(c, "confidence") or not isinstance(c.confidence, int):
            return 0.0
        if not (0 <= c.confidence <= 100):
            return 0.0
    return 100.0


@pytest.mark.parametrize("mandate_id", MANDATE_IDS)
@pytest.mark.asyncio
async def test_agt02_eval(mandate_id, eval_results, mock_agent_llm):
    """AGT-02 scores completeness + format ≥ 80 on each golden mandate."""
    golden = load_golden(mandate_id)
    mandate = golden["input_mandate"]
    client_profile = {"industry": "consumer_goods", "existing_competitors": []}

    # Configure mock to return golden competitors
    if mock_agent_llm is not None:
        import json
        from unittest.mock import MagicMock
        golden_competitors = golden["golden_outputs"]["agt02_competitors"]
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps({"competitors": golden_competitors}))]
        mock_agent_llm.messages.create.return_value = mock_response

    competitors = await identify_competitors_sync(mandate, client_profile)

    completeness = _score_completeness_agt02(competitors)
    fmt = _score_format_agt02(competitors)

    card = ScoreCard(
        agent_id="AGT-02",
        agent_name="CompetitiveIntel",
        mandate_id=mandate_id,
        completeness=completeness,
        format_score=fmt,
    )
    eval_results.append(card)

    assert card.overall >= PASS_THRESHOLD, (
        f"AGT-02 on {mandate_id}: overall={card.overall:.1f} "
        f"(completeness={completeness}, format={fmt})"
    )
```

- [ ] **Step 2: Run and verify 3 tests pass**

```bash
$env:PYTHONPATH = "."
pytest backend/tests/agents/test_eval_agt02.py -v --no-header -p no:warnings
```

Expected: `3 passed`.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/agents/test_eval_agt02.py
git commit -m "feat(evals): add AGT-02 CompetitiveIntel eval tests

Co-authored-by: katharguppe <katharguppe@users.noreply.github.com>"
```

---

### Task 5: test_eval_agt03.py — CampaignStrategist evals (with coherence)

**Files:**
- Create: `backend/tests/agents/test_eval_agt03.py`

AGT-03 entry point: `campaign_strategist_agent(mandate: Dict, ci_report: Dict) -> Dict`
Returns: `{"campaigns": List[dict], "validation_errors": list, "regeneration_log": list}`
Each campaign dict has: `name`, `tagline`, `strategic_narrative`, `campaign_theme`, `audience_segmentation`, `channel_mix`, `message_architecture`, `campaign_phasing`, `tone_board`, `mandate_fit_score`, `gap_exploitation_score`.
Scoring: completeness + format + coherence (AGT-03 is the only agent with coherence).

- [ ] **Step 1: Create test_eval_agt03.py**

```python
"""Eval tests for AGT-03 CampaignStrategist (includes coherence scoring)."""
import json
import pytest
from anthropic import AsyncAnthropic
from unittest.mock import AsyncMock, MagicMock

from backend.app.agents.campaign_strategist import campaign_strategist_agent
from backend.tests.agents.conftest_evals import (
    ScoreCard, load_golden, score_completeness, score_format,
    score_coherence, PASS_THRESHOLD
)

MANDATE_IDS = ["mandate_1", "mandate_2", "mandate_3"]

REQUIRED_OUTPUT_FIELDS = ["campaigns", "validation_errors", "regeneration_log"]
REQUIRED_OUTPUT_TYPES = {
    "campaigns": list,
    "validation_errors": list,
    "regeneration_log": list,
}
REQUIRED_CAMPAIGN_FIELDS = [
    "name", "tagline", "strategic_narrative", "campaign_theme",
    "audience_segmentation", "channel_mix", "message_architecture",
    "campaign_phasing", "tone_board", "mandate_fit_score", "gap_exploitation_score"
]


def _score_completeness_agt03(output: dict) -> float:
    """Score on top-level output keys + completeness of first campaign."""
    top_score = score_completeness(output, REQUIRED_OUTPUT_FIELDS)
    campaigns = output.get("campaigns", [])
    if not campaigns:
        return top_score * 0.3  # heavy penalty for no campaigns
    first = campaigns[0] if isinstance(campaigns[0], dict) else campaigns[0].model_dump()
    campaign_score = score_completeness(first, REQUIRED_CAMPAIGN_FIELDS)
    return round(0.3 * top_score + 0.7 * campaign_score, 1)


def _make_golden_campaign_response(golden_concept: dict) -> str:
    """Build a realistic LLM response mimicking CampaignConcept JSON."""
    concept = {
        "name": golden_concept["name"],
        "tagline": golden_concept["tagline"],
        "strategic_narrative": golden_concept["strategic_narrative"],
        "campaign_theme": golden_concept["campaign_theme"],
        "audience_segmentation": golden_concept["audience_segmentation"],
        "channel_mix": [
            {
                "channel": c["channel"],
                "rationale": c["rationale"],
                "competitor_gap": c["competitor_gap"],
            }
            for c in golden_concept["channel_mix"]
        ],
        "message_architecture": golden_concept["message_architecture"],
        "campaign_phasing": golden_concept["campaign_phasing"],
        "tone_board": golden_concept["tone_board"],
        "risk_flags": {"legal": None, "regulatory": None, "sensitivity": None},
        "mandate_fit_score": golden_concept["mandate_fit_score"],
        "gap_exploitation_score": golden_concept["gap_exploitation_score"],
    }
    return json.dumps(concept)


@pytest.mark.parametrize("mandate_id", MANDATE_IDS)
@pytest.mark.asyncio
async def test_agt03_eval(mandate_id, eval_results, mock_agent_llm):
    """AGT-03 scores completeness + format + coherence ≥ 80 on each golden mandate."""
    golden = load_golden(mandate_id)
    mandate = golden["input_mandate"]
    golden_concept = golden["golden_outputs"]["agt03_concept"]
    golden_competitors = golden["golden_outputs"]["agt02_competitors"]

    ci_report = {
        "competitors": golden_competitors,
        "whitespace_opportunities": {
            "untapped_channels": ["TikTok"],
            "messaging_gaps": ["authenticity"],
            "geographic_gaps": [],
        },
        "market_concentration": "fragmented",
    }

    # Configure mock to return a realistic campaign concept
    if mock_agent_llm is not None:
        campaign_json = _make_golden_campaign_response(golden_concept)
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=campaign_json)]
        mock_agent_llm.messages.create.return_value = mock_response

    output = await campaign_strategist_agent(mandate, ci_report)

    # Normalize campaigns list to dicts
    campaigns = output.get("campaigns", [])
    campaigns_as_dicts = []
    for c in campaigns:
        if hasattr(c, "model_dump"):
            campaigns_as_dicts.append(c.model_dump())
        elif isinstance(c, dict):
            campaigns_as_dicts.append(c)
    output_for_scoring = {**output, "campaigns": campaigns_as_dicts}

    completeness = _score_completeness_agt03(output_for_scoring)
    fmt = score_format(output_for_scoring, REQUIRED_OUTPUT_TYPES)

    # Coherence: compare first campaign to golden
    if mock_agent_llm is not None:
        # Mock coherence returns 85
        coherence_mock = MagicMock()
        coherence_response = MagicMock()
        coherence_response.content = [MagicMock(text='{"score": 85}')]
        coherence_mock.messages.create = AsyncMock(return_value=coherence_response)
        coherence = await score_coherence(
            campaigns_as_dicts[0] if campaigns_as_dicts else {},
            golden_concept,
            coherence_mock,
        )
    else:
        client = AsyncAnthropic()
        coherence = await score_coherence(
            campaigns_as_dicts[0] if campaigns_as_dicts else {},
            golden_concept,
            client,
        )

    card = ScoreCard(
        agent_id="AGT-03",
        agent_name="CampaignStrategist",
        mandate_id=mandate_id,
        completeness=completeness,
        format_score=fmt,
        coherence=coherence,
    )
    eval_results.append(card)

    assert card.overall >= PASS_THRESHOLD, (
        f"AGT-03 on {mandate_id}: overall={card.overall:.1f} "
        f"(completeness={completeness}, format={fmt}, coherence={coherence})"
    )
```

- [ ] **Step 2: Run and verify 3 tests pass**

```bash
$env:PYTHONPATH = "."
pytest backend/tests/agents/test_eval_agt03.py -v --no-header -p no:warnings
```

Expected: `3 passed`.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/agents/test_eval_agt03.py
git commit -m "feat(evals): add AGT-03 CampaignStrategist eval tests with coherence scoring

Co-authored-by: katharguppe <katharguppe@users.noreply.github.com>"
```

---

### Task 6: test_eval_agt04.py — MediaPlanner evals

**Files:**
- Create: `backend/tests/agents/test_eval_agt04.py`

AGT-04 entry point: `media_planner_agent(campaign_concept: Dict, budget_envelope: Dict, mandate_geography: Dict) -> Dict`
Returns: `{"activations": list, "budget_summary": ..., "validation_errors": list, "allocation_log": list, "status": str}`
Scoring: completeness + format only.

- [ ] **Step 1: Create test_eval_agt04.py**

```python
"""Eval tests for AGT-04 MediaPlanner."""
import pytest
from backend.app.agents.media_planner import media_planner_agent
from backend.tests.agents.conftest_evals import (
    ScoreCard, load_golden, score_completeness, score_format, PASS_THRESHOLD
)

MANDATE_IDS = ["mandate_1", "mandate_2", "mandate_3"]

REQUIRED_OUTPUT_FIELDS = ["activations", "budget_summary", "validation_errors", "allocation_log", "status"]
REQUIRED_OUTPUT_TYPES = {
    "activations": list,
    "validation_errors": list,
    "allocation_log": list,
    "status": str,
}


def _build_campaign_concept(golden: dict) -> dict:
    """Build a campaign_concept input from the golden agt03 output."""
    c = golden["golden_outputs"]["agt03_concept"]
    return {
        "channel_mix": [
            {"channel": ch["channel"], "weight": 1.0 / len(c["channel_mix"])}
            for ch in c["channel_mix"]
        ],
        "campaign_phasing": c["campaign_phasing"],
        "tone_board": c["tone_board"],
        "message_architecture": c["message_architecture"],
        "campaign_theme": c["campaign_theme"],
    }


@pytest.mark.parametrize("mandate_id", MANDATE_IDS)
@pytest.mark.asyncio
async def test_agt04_eval(mandate_id, eval_results, mock_agent_llm):
    """AGT-04 scores completeness + format ≥ 80 on each golden mandate."""
    golden = load_golden(mandate_id)
    mandate = golden["input_mandate"]
    campaign_concept = _build_campaign_concept(golden)
    budget_envelope = {
        "total_budget": mandate["budget"]["total_amount"],
        "currency": mandate["budget"]["currency"],
        "contingency_pct": 0.10,
    }
    mandate_geography = mandate["geography"]

    output = await media_planner_agent(campaign_concept, budget_envelope, mandate_geography)

    completeness = score_completeness(output, REQUIRED_OUTPUT_FIELDS)
    fmt = score_format(output, REQUIRED_OUTPUT_TYPES)

    card = ScoreCard(
        agent_id="AGT-04",
        agent_name="MediaPlanner",
        mandate_id=mandate_id,
        completeness=completeness,
        format_score=fmt,
    )
    eval_results.append(card)

    assert card.overall >= PASS_THRESHOLD, (
        f"AGT-04 on {mandate_id}: overall={card.overall:.1f} "
        f"(completeness={completeness}, format={fmt})"
    )
```

- [ ] **Step 2: Run and verify 3 tests pass**

```bash
$env:PYTHONPATH = "."
pytest backend/tests/agents/test_eval_agt04.py -v --no-header -p no:warnings
```

Expected: `3 passed`.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/agents/test_eval_agt04.py
git commit -m "feat(evals): add AGT-04 MediaPlanner eval tests

Co-authored-by: katharguppe <katharguppe@users.noreply.github.com>"
```

---

### Task 7: test_eval_agt05.py — BudgetOptimizer evals

**Files:**
- Create: `backend/tests/agents/test_eval_agt05.py`

AGT-05 entry point: `budget_optimizer_agent(activations: List[Dict], budget_envelope: Dict, campaign_context: Dict) -> Dict`
Returns: `{"optimized_activations": list, "roi_analysis": dict, "optimization_report": dict, "validation_errors": list, "status": str}`
Scoring: completeness + format only.

- [ ] **Step 1: Create test_eval_agt05.py**

```python
"""Eval tests for AGT-05 BudgetOptimizer."""
import pytest
from backend.app.agents.budget_optimizer import budget_optimizer_agent
from backend.tests.agents.conftest_evals import (
    ScoreCard, load_golden, score_completeness, score_format, PASS_THRESHOLD
)

MANDATE_IDS = ["mandate_1", "mandate_2", "mandate_3"]

REQUIRED_OUTPUT_FIELDS = [
    "optimized_activations", "roi_analysis", "optimization_report",
    "validation_errors", "status"
]
REQUIRED_OUTPUT_TYPES = {
    "optimized_activations": list,
    "roi_analysis": dict,
    "optimization_report": dict,
    "validation_errors": list,
    "status": str,
}

_SAMPLE_ACTIVATION = {
    "id": "act-001",
    "channel_enum": "Social",
    "sub_channel": "Instagram",
    "format": "Feed",
    "geography": "SG",
    "placement": "feed",
    "phase": "Awareness",
    "scheduled_date": "2026-06-01",
    "duration": 14,
    "frequency": "daily",
    "audience_segment": "Primary",
    "estimated_reach": 100000,
    "estimated_cpm": 5.0,
    "cost_estimated": 25000.0,
    "message_version_ref": "msg-v1",
    "lead_time_days": 7,
    "offline_constraints": None,
}


def _build_activations(budget: float) -> list:
    """Build minimal activation list for budget optimizer input."""
    act = dict(_SAMPLE_ACTIVATION)
    act["cost_estimated"] = budget * 0.5
    act2 = dict(_SAMPLE_ACTIVATION)
    act2["id"] = "act-002"
    act2["sub_channel"] = "TikTok"
    act2["cost_estimated"] = budget * 0.5
    return [act, act2]


@pytest.mark.parametrize("mandate_id", MANDATE_IDS)
@pytest.mark.asyncio
async def test_agt05_eval(mandate_id, eval_results, mock_agent_llm):
    """AGT-05 scores completeness + format ≥ 80 on each golden mandate."""
    golden = load_golden(mandate_id)
    mandate = golden["input_mandate"]
    budget = mandate["budget"]["total_amount"]

    activations = _build_activations(budget)
    budget_envelope = {"total_budget": budget, "currency": mandate["budget"]["currency"]}
    campaign_context = {
        "campaign_name": mandate["campaign_concept"]["name"],
        "tone_board": golden["golden_outputs"]["agt03_concept"]["tone_board"],
        "target_audience": mandate["campaign_concept"]["target_audience"],
    }

    output = await budget_optimizer_agent(activations, budget_envelope, campaign_context)

    completeness = score_completeness(output, REQUIRED_OUTPUT_FIELDS)
    fmt = score_format(output, REQUIRED_OUTPUT_TYPES)

    card = ScoreCard(
        agent_id="AGT-05",
        agent_name="BudgetOptimizer",
        mandate_id=mandate_id,
        completeness=completeness,
        format_score=fmt,
    )
    eval_results.append(card)

    assert card.overall >= PASS_THRESHOLD, (
        f"AGT-05 on {mandate_id}: overall={card.overall:.1f} "
        f"(completeness={completeness}, format={fmt})"
    )
```

- [ ] **Step 2: Run and verify 3 tests pass**

```bash
$env:PYTHONPATH = "."
pytest backend/tests/agents/test_eval_agt05.py -v --no-header -p no:warnings
```

Expected: `3 passed`.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/agents/test_eval_agt05.py
git commit -m "feat(evals): add AGT-05 BudgetOptimizer eval tests

Co-authored-by: katharguppe <katharguppe@users.noreply.github.com>"
```

---

### Task 8: Full suite run + verify JSON report

**Files:** None (validation only)

- [ ] **Step 1: Run the full eval suite**

```bash
$env:PYTHONPATH = "."
pytest backend/tests/agents/test_eval_agt01.py \
       backend/tests/agents/test_eval_agt02.py \
       backend/tests/agents/test_eval_agt03.py \
       backend/tests/agents/test_eval_agt04.py \
       backend/tests/agents/test_eval_agt05.py \
       -v --no-header -p no:warnings -s
```

Expected:
- `15 passed` (3 mandates × 5 agents)
- Console table printed with per-agent scores
- `Report saved: docs/evals/results_<date>.json`

- [ ] **Step 2: Verify JSON report exists and is valid**

```bash
python -c "
import json, pathlib
p = sorted(pathlib.Path('docs/evals').glob('results_*.json'))[-1]
r = json.loads(p.read_text())
print('overall_pass:', r['overall_pass'])
print('agents:', [a['id'] + ' ' + str(a['overall']) for a in r['agents']])
"
```

Expected: `overall_pass: True` and all 5 agents listed with scores ≥ 80.

- [ ] **Step 3: Final commit**

```bash
git add backend/tests/agents/
git commit -m "feat(evals): TASK-029 complete — eval harness for AGT-01 through AGT-05

15 eval tests (3 mandates × 5 agents), all pass ≥ 80 threshold.
Console table + JSON report in docs/evals/.

Co-authored-by: katharguppe <katharguppe@users.noreply.github.com>"
```

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: conftest_evals` | PYTHONPATH not set | `$env:PYTHONPATH = "."` |
| `ScoreCard overall < 80` | Mock LLM returning error JSON | Check mock response text is valid JSON matching agent's expected format |
| `eval_results` always empty | `conftest_evals.py` not imported | Rename to `conftest.py` OR add `pytest_plugins = ["backend.tests.agents.conftest_evals"]` to root conftest |
| JSON report not written | `docs/evals/` not created | `EVALS_DIR.mkdir(parents=True, exist_ok=True)` already in reporter — check file permissions |
| AGT-03 coherence score is 0 | Mock coherence client not passed | Verify `coherence_mock.messages.create` is `AsyncMock` not `MagicMock` |
