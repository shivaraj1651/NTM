"""Tests for Campaign Service (TASK-012)."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from backend.app.services.campaign_service import CampaignService

# ---------------------------------------------------------------------------
# Helpers & fixtures
# ---------------------------------------------------------------------------

def _concept(concept_id: str | None = None) -> dict:
    cid = concept_id or str(uuid.uuid4())
    return {
        "id": cid,
        "name": "TikTok Gen-Z",
        "tagline": "Where Gen-Z discovers authenticity",
        "strategic_narrative": "Dominate TikTok.",
        "campaign_theme": "Authenticity Wins",
        "audience_segmentation": {"primary": "Gen-Z", "secondary": "Millennial", "tertiary": "Gen-X"},
        "channel_mix": [{"channel": "TikTok", "rationale": "native", "competitor_gap": "absent"}],
        "message_architecture": {"master_message": "Real stories", "channel_adaptations": {}},
        "campaign_phasing": {"awareness": "W1-2", "engagement": "W3-6", "conversion": "W7-12"},
        "tone_board": {"adjectives": ["bold", "innovative", "trustworthy", "energetic", "inclusive"], "visual_direction": "Bright"},
        "risk_flags": {"legal": None, "regulatory": None, "sensitivity": None},
        "mandate_fit_score": 9,
        "gap_exploitation_score": 10,
    }


def _mandate(mandate_id: str = "m-001") -> dict:
    return {
        "_id": mandate_id,
        "tenant_id": "t-001",
        "budget": {"total_amount": 100000, "currency": "USD"},
        "geography": {"regions": ["APAC"], "markets": ["India"], "country_list": ["IN"]},
        "campaign_concept": {"objective": "awareness"},
    }


def _ci_report(mandate_id: str = "m-001") -> dict:
    return {"_id": "ci-001", "mandate_id": mandate_id, "tenant_id": "t-001", "competitors": []}


def _campaign(
    campaign_id: str = "camp-001",
    status: str = "concepts_ready",
    concept_id: str | None = None,
) -> dict:
    cid = concept_id or str(uuid.uuid4())
    return {
        "_id": campaign_id,
        "tenant_id": "t-001",
        "mandate_id": "m-001",
        "status": status,
        "concepts": [_concept(cid)],
        "selected_concept_id": cid if status not in ("pending", "concepts_ready") else None,
        "activation_plan": [{"id": "act-1"}] if status in ("planned", "budget_proposed", "approved") else None,
        "budget_proposal": {"total_approved": 95000} if status in ("budget_proposed", "approved") else None,
        "created_at": datetime.now(UTC).isoformat(),
        "updated_at": datetime.now(UTC).isoformat(),
    }


def _make_db(campaigns_col, mandates_col, ci_reports_col):
    db = MagicMock()
    mapping = {
        "campaigns": campaigns_col,
        "mandates": mandates_col,
        "ci_reports": ci_reports_col,
    }
    db.__getitem__ = MagicMock(side_effect=lambda k: mapping[k])
    return db


# ---------------------------------------------------------------------------
# create()
# ---------------------------------------------------------------------------

class TestCreate:

    async def test_create_returns_concepts_ready(self):
        concept_id = str(uuid.uuid4())
        mandate = _mandate()
        ci = _ci_report()

        campaigns_col = AsyncMock()
        mandates_col = AsyncMock()
        ci_reports_col = AsyncMock()
        mandates_col.find_one = AsyncMock(return_value=mandate)
        ci_reports_col.find_one = AsyncMock(return_value=ci)
        campaigns_col.insert_one = AsyncMock(return_value=MagicMock())

        db = _make_db(campaigns_col, mandates_col, ci_reports_col)
        svc = CampaignService(db)

        with patch(
            "backend.app.services.campaign_service.campaign_strategist_agent",
            new=AsyncMock(return_value={"campaigns": [_concept(concept_id)], "validation_errors": [], "regeneration_log": []}),
        ):
            result = await svc.create("m-001", "t-001")

        assert result["status"] == "concepts_ready"
        assert len(result["concepts"]) == 1
        assert result["tenant_id"] == "t-001"
        campaigns_col.insert_one.assert_called_once()

    async def test_create_404_missing_mandate(self):
        campaigns_col = AsyncMock()
        mandates_col = AsyncMock()
        ci_reports_col = AsyncMock()
        mandates_col.find_one = AsyncMock(return_value=None)

        db = _make_db(campaigns_col, mandates_col, ci_reports_col)
        svc = CampaignService(db)

        with pytest.raises(HTTPException) as exc:
            await svc.create("m-missing", "t-001")
        assert exc.value.status_code == 404

    async def test_create_proceeds_without_ci_report(self):
        """CI report is optional now — create() proceeds with empty CI context."""
        campaigns_col = AsyncMock()
        mandates_col = AsyncMock()
        ci_reports_col = AsyncMock()
        mandates_col.find_one = AsyncMock(return_value=_mandate())
        ci_reports_col.find_one = AsyncMock(return_value=None)

        db = _make_db(campaigns_col, mandates_col, ci_reports_col)
        svc = CampaignService(db)

        with patch(
            "backend.app.services.campaign_service.campaign_strategist_agent",
            new=AsyncMock(return_value={"campaigns": [{"id": "concept-1", "name": "C1"}]}),
        ):
            result = await svc.create("m-001", "t-001")
        assert result["status"] == "concepts_ready"


# ---------------------------------------------------------------------------
# get()
# ---------------------------------------------------------------------------

class TestGet:

    async def test_get_returns_campaign(self):
        doc = _campaign()
        campaigns_col = AsyncMock()
        campaigns_col.find_one = AsyncMock(return_value=doc)

        db = _make_db(campaigns_col, AsyncMock(), AsyncMock())
        svc = CampaignService(db)

        result = await svc.get("camp-001", "t-001")
        assert result["_id"] == "camp-001"
        campaigns_col.find_one.assert_called_once_with({"_id": "camp-001", "tenant_id": "t-001"})

    async def test_get_404_wrong_tenant(self):
        campaigns_col = AsyncMock()
        campaigns_col.find_one = AsyncMock(return_value=None)

        db = _make_db(campaigns_col, AsyncMock(), AsyncMock())
        svc = CampaignService(db)

        with pytest.raises(HTTPException) as exc:
            await svc.get("camp-001", "t-wrong")
        assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# confirm()
# ---------------------------------------------------------------------------

class TestConfirm:

    async def test_confirm_sets_selected_concept_and_status(self):
        concept_id = str(uuid.uuid4())
        doc = _campaign(status="concepts_ready", concept_id=concept_id)
        doc["selected_concept_id"] = None

        campaigns_col = AsyncMock()
        campaigns_col.find_one = AsyncMock(return_value=doc)
        campaigns_col.find_one_and_update = AsyncMock(
            return_value={**doc, "status": "confirmed", "selected_concept_id": concept_id}
        )

        db = _make_db(campaigns_col, AsyncMock(), AsyncMock())
        svc = CampaignService(db)

        result = await svc.confirm("camp-001", concept_id, "t-001")
        assert result["status"] == "confirmed"
        assert result["selected_concept_id"] == concept_id

    async def test_confirm_409_wrong_status(self):
        doc = _campaign(status="confirmed")
        campaigns_col = AsyncMock()
        campaigns_col.find_one = AsyncMock(return_value=doc)

        db = _make_db(campaigns_col, AsyncMock(), AsyncMock())
        svc = CampaignService(db)

        with pytest.raises(HTTPException) as exc:
            await svc.confirm("camp-001", doc["selected_concept_id"], "t-001")
        assert exc.value.status_code == 409

    async def test_confirm_422_invalid_concept_id(self):
        doc = _campaign(status="concepts_ready")
        campaigns_col = AsyncMock()
        campaigns_col.find_one = AsyncMock(return_value=doc)

        db = _make_db(campaigns_col, AsyncMock(), AsyncMock())
        svc = CampaignService(db)

        with pytest.raises(HTTPException) as exc:
            await svc.confirm("camp-001", "not-a-real-concept-id", "t-001")
        assert exc.value.status_code == 422


# ---------------------------------------------------------------------------
# get_activation_plan()
# ---------------------------------------------------------------------------

class TestGetActivationPlan:

    async def test_get_activation_plan_triggers_agt04(self):
        concept_id = str(uuid.uuid4())
        doc = _campaign(status="confirmed", concept_id=concept_id)
        doc["selected_concept_id"] = concept_id
        doc["activation_plan"] = None
        mandate = _mandate()

        campaigns_col = AsyncMock()
        campaigns_col.find_one = AsyncMock(return_value=doc)
        campaigns_col.find_one_and_update = AsyncMock(
            return_value={**doc, "status": "planned", "activation_plan": [{"id": "act-1"}]}
        )
        mandates_col = AsyncMock()
        mandates_col.find_one = AsyncMock(return_value=mandate)

        db = _make_db(campaigns_col, mandates_col, AsyncMock())
        svc = CampaignService(db)

        with patch(
            "backend.app.services.campaign_service.media_planner_agent",
            new=AsyncMock(return_value={"activations": [{"id": "act-1"}], "budget_summary": {}}),
        ):
            result = await svc.get_activation_plan("camp-001", "t-001")

        assert result["status"] == "planned"
        assert result["activation_plan"] is not None

    async def test_get_activation_plan_cached(self):
        doc = _campaign(status="planned")  # already has activation_plan

        campaigns_col = AsyncMock()
        campaigns_col.find_one = AsyncMock(return_value=doc)

        db = _make_db(campaigns_col, AsyncMock(), AsyncMock())
        svc = CampaignService(db)

        mock_agt04 = AsyncMock()
        with patch("backend.app.services.campaign_service.media_planner_agent", new=mock_agt04):
            result = await svc.get_activation_plan("camp-001", "t-001")

        mock_agt04.assert_not_called()
        assert result["activation_plan"] is not None

    async def test_get_activation_plan_409_not_confirmed(self):
        doc = _campaign(status="concepts_ready")
        campaigns_col = AsyncMock()
        campaigns_col.find_one = AsyncMock(return_value=doc)

        db = _make_db(campaigns_col, AsyncMock(), AsyncMock())
        svc = CampaignService(db)

        with pytest.raises(HTTPException) as exc:
            await svc.get_activation_plan("camp-001", "t-001")
        assert exc.value.status_code == 409


# ---------------------------------------------------------------------------
# propose_budget()
# ---------------------------------------------------------------------------

class TestProposeBudget:

    async def test_propose_budget_triggers_agt05(self):
        doc = _campaign(status="planned")

        campaigns_col = AsyncMock()
        campaigns_col.find_one = AsyncMock(return_value=doc)
        campaigns_col.find_one_and_update = AsyncMock(
            return_value={**doc, "status": "budget_proposed", "budget_proposal": {"total_approved": 95000}}
        )
        mandates_col = AsyncMock()
        mandates_col.find_one = AsyncMock(return_value=_mandate())

        db = _make_db(campaigns_col, mandates_col, AsyncMock())
        svc = CampaignService(db)

        with patch(
            "backend.app.services.campaign_service.budget_optimizer_agent",
            new=AsyncMock(return_value={"total_approved": 95000, "optimization_report": {}}),
        ):
            result = await svc.propose_budget("camp-001", "t-001")

        assert result["status"] == "budget_proposed"
        assert result["budget_proposal"] is not None

    async def test_propose_budget_409_wrong_status(self):
        doc = _campaign(status="confirmed")
        campaigns_col = AsyncMock()
        campaigns_col.find_one = AsyncMock(return_value=doc)

        db = _make_db(campaigns_col, AsyncMock(), AsyncMock())
        svc = CampaignService(db)

        with pytest.raises(HTTPException) as exc:
            await svc.propose_budget("camp-001", "t-001")
        assert exc.value.status_code == 409


# ---------------------------------------------------------------------------
# confirm_budget()
# ---------------------------------------------------------------------------

class TestConfirmBudget:

    async def test_confirm_budget_sets_approved(self):
        doc = _campaign(status="budget_proposed")

        campaigns_col = AsyncMock()
        campaigns_col.find_one = AsyncMock(return_value=doc)
        campaigns_col.find_one_and_update = AsyncMock(
            return_value={**doc, "status": "approved"}
        )

        db = _make_db(campaigns_col, AsyncMock(), AsyncMock())
        svc = CampaignService(db)

        result = await svc.confirm_budget("camp-001", "t-001")
        assert result["status"] == "approved"

    async def test_confirm_budget_409_wrong_status(self):
        doc = _campaign(status="planned")
        campaigns_col = AsyncMock()
        campaigns_col.find_one = AsyncMock(return_value=doc)

        db = _make_db(campaigns_col, AsyncMock(), AsyncMock())
        svc = CampaignService(db)

        with pytest.raises(HTTPException) as exc:
            await svc.confirm_budget("camp-001", "t-001")
        assert exc.value.status_code == 409
