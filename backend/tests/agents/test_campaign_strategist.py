"""Unit tests for Campaign Strategist Agent (AGT-03)."""

import pytest
from uuid import uuid4
from backend.app.schemas.campaign_concept import (
    CampaignConcept,
    AudienceSegmentation,
    ChannelRecommendation,
    MessageArchitecture,
    CampaignPhasing,
    ToneBoard,
    RiskFlags,
)
from backend.app.agents.campaign_strategist import CampaignConceptValidator, RiskFilter


# Sample valid campaign concept for reuse
def get_valid_campaign() -> dict:
    """Return a valid campaign concept dict."""
    return {
        "name": "TikTok Gen-Z",
        "tagline": "Where Gen-Z discovers authenticity",
        "strategic_narrative": "Competitors ignore TikTok; we dominate with authentic positioning.",
        "campaign_theme": "Authenticity Wins",
        "audience_segmentation": {
            "primary": "Gen-Z (16-24)",
            "secondary": "Millennial early adopters",
            "tertiary": "Gen-X curious"
        },
        "channel_mix": [
            {
                "channel": "TikTok",
                "rationale": "Primary audience native to platform",
                "competitor_gap": "Competitors absent or inauthentic"
            }
        ],
        "message_architecture": {
            "master_message": "Real stories, real people, real impact",
            "channel_adaptations": {"TikTok": "30-second storytelling format"}
        },
        "campaign_phasing": {
            "awareness": "Week 1-2: Seed with influencer partnerships",
            "engagement": "Week 3-6: User-generated content contests",
            "conversion": "Week 7-12: Product placement + direct calls-to-action"
        },
        "tone_board": {
            "adjectives": ["authentic", "bold", "witty", "inclusive", "innovative"],
            "visual_direction": "Bright, desaturated colors; hand-drawn graphics"
        },
        "risk_flags": {
            "legal": None,
            "regulatory": None,
            "sensitivity": None
        },
        "mandate_fit_score": 9,
        "gap_exploitation_score": 10
    }


class TestCampaignConceptValidator:
    """Tests for CampaignConceptValidator."""

    def test_validator_accepts_valid_campaign(self):
        """Validator should accept a fully valid campaign concept."""
        validator = CampaignConceptValidator()
        campaign = get_valid_campaign()

        errors = validator.validate_schema(campaign)

        assert errors == [], f"Expected no errors, got: {errors}"

    def test_validator_detects_missing_required_field(self):
        """Validator should detect missing required fields."""
        validator = CampaignConceptValidator()
        campaign = get_valid_campaign()
        del campaign["name"]  # Remove required field

        errors = validator.validate_schema(campaign)

        assert len(errors) > 0, "Expected validation error for missing 'name'"
        assert any("name" in error for error in errors)

    def test_validator_detects_missing_nested_field(self):
        """Validator should detect missing nested fields."""
        validator = CampaignConceptValidator()
        campaign = get_valid_campaign()
        del campaign["audience_segmentation"]["primary"]

        errors = validator.validate_schema(campaign)

        assert len(errors) > 0
        assert any("primary" in error for error in errors)

    def test_validator_detects_wrong_adjective_count(self):
        """Validator should enforce exactly 5 adjectives in tone_board."""
        validator = CampaignConceptValidator()
        campaign = get_valid_campaign()
        campaign["tone_board"]["adjectives"] = ["authentic", "bold"]  # Only 2

        errors = validator.validate_schema(campaign)

        assert len(errors) > 0
        assert any("adjectives" in error and "5" in error for error in errors)

    def test_validator_detects_invalid_score_range(self):
        """Validator should enforce scores are 1-10."""
        validator = CampaignConceptValidator()
        campaign = get_valid_campaign()
        campaign["mandate_fit_score"] = 15  # Out of range

        errors = validator.validate_schema(campaign)

        assert len(errors) > 0
        assert any("mandate_fit_score" in error for error in errors)

    def test_validator_detects_empty_channel_mix(self):
        """Validator should require at least 1 channel in channel_mix."""
        validator = CampaignConceptValidator()
        campaign = get_valid_campaign()
        campaign["channel_mix"] = []

        errors = validator.validate_schema(campaign)

        assert len(errors) > 0
        assert any("channel_mix" in error for error in errors)


class TestRiskFilter:
    """Tests for RiskFilter class."""

    def test_risk_filter_detects_legal_risk(self):
        """Risk filter should detect legal risk in campaign."""
        risk_filter = RiskFilter()
        campaign = get_valid_campaign()
        campaign["risk_flags"]["legal"] = "Unsubstantiated benefit claim"

        should_regen = risk_filter.should_regenerate(campaign["risk_flags"])

        assert should_regen is True

    def test_risk_filter_detects_regulatory_risk(self):
        """Risk filter should detect regulatory risk."""
        risk_filter = RiskFilter()
        campaign = get_valid_campaign()
        campaign["risk_flags"]["regulatory"] = "Geographic compliance issue in EMEA"

        should_regen = risk_filter.should_regenerate(campaign["risk_flags"])

        assert should_regen is True

    def test_risk_filter_detects_sensitivity_risk(self):
        """Risk filter should detect sensitivity risk."""
        risk_filter = RiskFilter()
        campaign = get_valid_campaign()
        campaign["risk_flags"]["sensitivity"] = "Tone misaligned with brand guidelines"

        should_regen = risk_filter.should_regenerate(campaign["risk_flags"])

        assert should_regen is True

    def test_risk_filter_clears_campaign_with_no_risks(self):
        """Risk filter should not regenerate campaign with all nulls."""
        risk_filter = RiskFilter()
        campaign = get_valid_campaign()
        # risk_flags already have all None

        should_regen = risk_filter.should_regenerate(campaign["risk_flags"])

        assert should_regen is False

    def test_risk_filter_returns_legal_regeneration_prompt(self):
        """Risk filter should provide correct regeneration prompt for legal risk."""
        risk_filter = RiskFilter()

        prompt = risk_filter.get_regeneration_prompt("legal")

        assert "unsubstantiated" in prompt.lower() or "claims" in prompt.lower()

    def test_risk_filter_returns_regulatory_regeneration_prompt(self):
        """Risk filter should provide correct regeneration prompt for regulatory risk."""
        risk_filter = RiskFilter()

        prompt = risk_filter.get_regeneration_prompt("regulatory")

        assert "compliance" in prompt.lower() or "regulation" in prompt.lower()

    def test_risk_filter_returns_sensitivity_regeneration_prompt(self):
        """Risk filter should provide correct regeneration prompt for sensitivity risk."""
        risk_filter = RiskFilter()

        prompt = risk_filter.get_regeneration_prompt("sensitivity")

        assert "tone" in prompt.lower() or "brand" in prompt.lower()
