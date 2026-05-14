---
title: Agent Eval Harness Design (TASK-029)
date: 2026-05-14
status: approved
---

# Agent Eval Harness — TASK-029

## Goal

Build a repeatable eval harness for NTM agents AGT-01 through AGT-05. Each agent runs against 3 seeded test mandates and is scored on completeness, format, and (for LLM agents) coherence. All agents must score ≥ 80 before Phase 4 begins.

## Approach

One pytest file per agent (Option A). Follows existing `test_<agent>.py` naming convention. Shared `conftest_evals.py` provides the Haiku mock, `--live` marker, and JSON reporter. Golden datasets are hardcoded JSON fixtures committed to `docs/golden/`.

## Module Scope

`backend/tests/agents/` + `docs/golden/` ONLY. No changes to agent source code.

## File Structure

```
docs/golden/
  mandate_1_concept.json       # golden reference for test mandate 1
  mandate_2_concept.json       # golden reference for test mandate 2
  mandate_3_concept.json       # golden reference for test mandate 3

backend/tests/agents/
  conftest_evals.py            # shared: Haiku mock, --live marker, JSON reporter
  test_eval_agt01.py           # MandateAnalyst evals (completeness + format)
  test_eval_agt02.py           # CompetitiveIntel evals (completeness + format)
  test_eval_agt03.py           # CampaignStrategist evals (all 3 scores, golden compare)
  test_eval_agt04.py           # MediaPlanner evals (completeness + format)
  test_eval_agt05.py           # BudgetOptimizer evals (completeness + format)

docs/evals/
  .gitkeep                     # directory tracked; report files not committed
```

## Golden Dataset Format

Each `docs/golden/mandate_N_concept.json` contains:

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
      "objective": "Increase brand awareness among 18-45 urban demographic",
      "description": "Q2 campaign across digital and offline channels",
      "target_audience": "18-45 urban professionals",
      "timeline": "June-July 2026"
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
      "completeness_score": 17,
      "missing_fields": []
    },
    "agt03_concept": {
      "campaign_concept": {
        "name": "Summer Refresh 2026",
        "objective": "Drive brand awareness in SEA among urban 18-45 demographic",
        "key_messages": ["Refresh your summer", "Connect with your city"]
      },
      "target_segments": ["Primary: Urban 25-35", "Secondary: 18-24 students"],
      "channel_mix": ["Instagram", "TikTok", "OOH"],
      "estimated_reach": 2500000
    }
  }
}
```

Three golden files (mandate_1, mandate_2, mandate_3) cover distinct geographies, budgets, and campaign types to test agent robustness.

## Scoring Profiles

| Agent | completeness | format | coherence | Formula | Threshold |
|---|---|---|---|---|---|
| AGT-01 | ✓ | ✓ | — | 0.5c + 0.5f | ≥ 80 |
| AGT-02 | ✓ | ✓ | — | 0.5c + 0.5f | ≥ 80 |
| AGT-03 | ✓ | ✓ | ✓ (Haiku) | 0.4c + 0.3f + 0.3h | ≥ 80 |
| AGT-04 | ✓ | ✓ | — | 0.5c + 0.5f | ≥ 80 |
| AGT-05 | ✓ | ✓ | — | 0.5c + 0.5f | ≥ 80 |

### Score Definitions

**completeness_score** (0–100):
`(required output fields present / total required fields) × 100`
Each agent has a defined `REQUIRED_OUTPUT_FIELDS` list in its eval file.

**format_score** (0 or 100, binary):
- 100 if: output is valid JSON + all top-level required keys exist at the correct Python type
- 0 otherwise

**coherence_score** (0–100, AGT-03 only):
Haiku prompt: `"Rate the coherence and completeness of this agent output compared to the golden reference on a scale of 0–100. Return JSON {\"score\": N}."`
Input: golden_outputs.agt03_concept + agent output dict.

**overall_score**:
Weighted sum per scoring profile. Agent passes if `overall_score >= 80`.

## Pytest Marker & Execution Modes

**Fast mode (default, no API calls):**
```bash
pytest backend/tests/agents/test_eval_agt01.py -v
pytest backend/tests/agents/ -k "eval" -v
```
`mock_haiku_coherence` fixture patches Anthropic client → always returns `{"score": 85}`.

**Live mode (real Haiku, requires ANTHROPIC_API_KEY):**
```bash
pytest backend/tests/agents/test_eval_agt03.py -m live -v
```
Skips mock, calls `claude-haiku-4-5-20251001` for coherence scoring.

Marker registration in `conftest_evals.py`:
```python
def pytest_configure(config):
    config.addinivalue_line("markers", "live: make real Anthropic API calls for coherence scoring")
```

## Report Output

### Console Table (printed after all evals complete)

```
NTM Agent Eval Results  2026-05-14  [mode: mock]
──────────────────────────────────────────────────
Agent   completeness  format  coherence  overall
AGT-01  95.0          100     —          97.5   ✓
AGT-02  88.2          100     —          94.1   ✓
AGT-03  91.0          100     85.0       91.7   ✓
AGT-04  87.5          100     —          93.8   ✓
AGT-05  93.0          100     —          96.5   ✓
──────────────────────────────────────────────────
Overall: PASS  5/5 agents ≥ 80
```

### JSON Report (`docs/evals/results_YYYY-MM-DD.json`)

```json
{
  "run_date": "2026-05-14",
  "mode": "mock",
  "threshold": 80,
  "overall_pass": true,
  "agents": [
    {
      "id": "AGT-01",
      "name": "MandateAnalyst",
      "completeness": 95.0,
      "format": 100,
      "coherence": null,
      "overall": 97.5,
      "pass": true,
      "mandates_tested": 3
    }
  ]
}
```

`docs/evals/` is in `.gitignore` for `*.json` files; only `.gitkeep` is committed.

## conftest_evals.py Responsibilities

- Register `live` marker
- `mock_haiku_coherence` autouse fixture: patches `anthropic.AsyncAnthropic` unless `-m live` active
- `eval_results` session-scoped fixture: accumulates `ScoreCard` objects from all eval files
- `json_reporter` session-scoped fixture (autouse): writes JSON + prints console table after session ends
- `load_golden(mandate_id)` helper: loads `docs/golden/mandate_{N}_concept.json`

## Data Flow

```
docs/golden/mandate_N_concept.json
        ↓ load_golden()
input_mandate → Agent.run() → output dict
                                  ↓
                        score_completeness()   ← REQUIRED_OUTPUT_FIELDS
                        score_format()         ← type schema
                        [score_coherence()]    ← Haiku / mock
                                  ↓
                           ScoreCard(agent_id, mandate_id, scores)
                                  ↓
                        assert overall >= 80
                                  ↓
               eval_results[] → json_reporter → console + JSON file
```

## Out of Scope

- AGT-06 through AGT-15 (future tasks)
- Celery Beat scheduling of evals
- Database storage of eval history
- CI integration of `--live` mode (mock mode runs in CI automatically via existing workflow)
