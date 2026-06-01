import pytest
from pydantic import ValidationError

from backend.app.schemas.campaign import (
    CampaignConfirmRequest,
    CampaignCreateRequest,
    CampaignResponse,
    CampaignStatusEnum,
    CampaignUpdateRequest,
)


def _base_doc(**overrides):
    doc = {
        "id": "abc123",
        "tenant_id": "t1",
        "mandate_id": "m1",
        "status": "pending",
        "concepts": [],
    }
    doc.update(overrides)
    return doc


def test_response_from_mongo_doc():
    doc = {
        "_id": "abc123",
        "tenant_id": "t1",
        "mandate_id": "m1",
        "status": "pending",
        "concepts": [],
    }
    resp = CampaignResponse.model_validate(doc)
    assert resp.id == "abc123"


def test_response_from_id_key():
    resp = CampaignResponse.model_validate(_base_doc(status="concepts_ready"))
    assert resp.id == "abc123"


def test_status_enum_valid():
    for status in ["pending", "concepts_ready", "confirmed", "planned", "budget_proposed", "approved"]:
        resp = CampaignResponse.model_validate(_base_doc(status=status))
        assert resp.status == CampaignStatusEnum(status)


def test_status_enum_invalid():
    with pytest.raises(ValidationError):
        CampaignResponse.model_validate(_base_doc(status="INVALID"))


def test_create_request_requires_mandate_id():
    with pytest.raises(ValidationError):
        CampaignCreateRequest()


def test_update_request_all_none():
    req = CampaignUpdateRequest()
    assert req.mandate_id is None
    assert req.selected_concept_id is None


def test_confirm_request_requires_concept_id():
    with pytest.raises(ValidationError):
        CampaignConfirmRequest()


def test_response_both_id_and_mongo_id_id_wins():
    doc = {
        "_id": "should_be_ignored",
        "id": "real_id",
        "tenant_id": "t1",
        "mandate_id": "m1",
        "status": "pending",
        "concepts": [],
    }
    resp = CampaignResponse.model_validate(doc)
    assert resp.id == "real_id"


def test_response_missing_required_fields_raises():
    with pytest.raises(ValidationError):
        CampaignResponse.model_validate({"id": "x", "tenant_id": "t1"})
