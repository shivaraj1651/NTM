"""Tests for campaign strategist agent (AGT-03)."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.app.agents.campaign_strategist import (
    CampaignConceptValidator,
    RiskFilter,
    campaign_strategist_agent,
)


@pytest.fixture
def mock_anthropic_response():
    """Fixture: mock Claude API response with valid campaign concept."""
    def _response(campaign_num: int = 1) -> str:
        return json.dumps({
            "name": f"Campaign #{campaign_num}",
            "tagline": f"Campaign tagline #{campaign_num}",
            "strategic_narrative": f"Campaign narrative exploits gap #{campaign_num}.",
            "campaign_theme": f"Theme #{campaign_num}",
            "audience_segmentation": {
                "primary": f"Primary audience #{campaign_num}",
                "secondary": f"Secondary audience #{campaign_num}",
                "tertiary": f"Tertiary audience #{campaign_num}"
            },
            "channel_mix": [
                {
                    "channel": "TikTok",
                    "rationale": f"Rationale #{campaign_num}",
                    "competitor_gap": f"Gap #{campaign_num}"
                }
            ],
            "message_architecture": {
                "master_message": f"Master message #{campaign_num}",
                "channel_adaptations": {"TikTok": f"TikTok adaptation #{campaign_num}"}
            },
            "campaign_phasing": {
                "awareness": f"Awareness phase #{campaign_num}",
                "engagement": f"Engagement phase #{campaign_num}",
                "conversion": f"Conversion phase #{campaign_num}"
            },
            "tone_board": {
                "adjectives": ["authentic", "bold", "witty", "inclusive", "innovative"],
                "visual_direction": f"Visual direction #{campaign_num}"
            },
            "risk_flags": {"legal": None, "regulatory": None, "sensitivity": None},
            "mandate_fit_score": 9,
            "gap_exploitation_score": 8
        })
    return _response


class TestRiskFilter:
    """Test RiskFilter class."""

    def test_should_regenerate_with_no_risks(self):
        """Risk filter should return False when no risks detected."""
        risk_filter = RiskFilter()
        risk_flags = {"legal": None, "regulatory": None, "sensitivity": None}
        assert risk_filter.should_regenerate(risk_flags) is False

    def test_should_regenerate_with_legal_risk(self):
        """Risk filter should return True when legal risk detected."""
        risk_filter = RiskFilter()
        risk_flags = {"legal": "Unsubstantiated claims", "regulatory": None, "sensitivity": None}
        assert risk_filter.should_regenerate(risk_flags) is True

    def test_should_regenerate_with_regulatory_risk(self):
        """Risk filter should return True when regulatory risk detected."""
        risk_filter = RiskFilter()
        risk_flags = {"legal": None, "regulatory": "GDPR violation", "sensitivity": None}
        assert risk_filter.should_regenerate(risk_flags) is True

    def test_should_regenerate_with_sensitivity_risk(self):
        """Risk filter should return True when sensitivity risk detected."""
        risk_filter = RiskFilter()
        risk_flags = {"legal": None, "regulatory": None, "sensitivity": "Offensive targeting"}
        assert risk_filter.should_regenerate(risk_flags) is True

    def test_should_regenerate_with_multiple_risks(self):
        """Risk filter should return True when multiple risks detected."""
        risk_filter = RiskFilter()
        risk_flags = {"legal": "Issue", "regulatory": "Issue", "sensitivity": "Issue"}
        assert risk_filter.should_regenerate(risk_flags) is True

    def test_get_regeneration_prompt_legal(self):
        """Get regeneration prompt for legal risk."""
        risk_filter = RiskFilter()
        prompt = risk_filter.get_regeneration_prompt("legal")
        assert "legal risk" in prompt.lower()
        assert "unsubstantiated claims" in prompt.lower()

    def test_get_regeneration_prompt_regulatory(self):
        """Get regeneration prompt for regulatory risk."""
        risk_filter = RiskFilter()
        prompt = risk_filter.get_regeneration_prompt("regulatory")
        assert "regulatory risk" in prompt.lower()
        assert "compliance" in prompt.lower()

    def test_get_regeneration_prompt_sensitivity(self):
        """Get regeneration prompt for sensitivity risk."""
        risk_filter = RiskFilter()
        prompt = risk_filter.get_regeneration_prompt("sensitivity")
        assert "sensitivity risk" in prompt.lower()
        assert "offensive" in prompt.lower() or "controversial" in prompt.lower()


class TestCampaignConceptValidator:
    """Test CampaignConceptValidator class."""

    def test_validate_schema_with_valid_campaign(self):
        """Validator should return empty errors list for valid campaign."""
        validator = CampaignConceptValidator()
        campaign = {
            "name": "Test Campaign",
            "tagline": "Test tagline",
            "strategic_narrative": "This is strategic",
            "campaign_theme": "Theme",
            "audience_segmentation": {"primary": "Gen-Z", "secondary": "Millennials", "tertiary": "Gen-X"},
            "channel_mix": [{"channel": "TikTok", "rationale": "High reach", "competitor_gap": "Gap"}],
            "message_architecture": {"master_message": "Message", "channel_adaptations": {"TikTok": "TikTok version"}},
            "campaign_phasing": {"awareness": "Phase 1", "engagement": "Phase 2", "conversion": "Phase 3"},
            "tone_board": {"adjectives": ["adj1", "adj2", "adj3", "adj4", "adj5"], "visual_direction": "Modern"},
            "risk_flags": {"legal": None, "regulatory": None, "sensitivity": None},
            "mandate_fit_score": 9,
            "gap_exploitation_score": 8,
        }
        errors = validator.validate_schema(campaign)
        assert errors == []

    def test_validate_schema_with_missing_field(self):
        """Validator should return error for missing required field."""
        validator = CampaignConceptValidator()
        campaign = {
            "name": "Test Campaign",
            # Missing many required fields
        }
        errors = validator.validate_schema(campaign)
        assert len(errors) > 0
        assert any("field" in e.lower() for e in errors)

    def test_validate_schema_with_invalid_type(self):
        """Validator should return error for invalid field type."""
        validator = CampaignConceptValidator()
        campaign = {
            "name": "Test Campaign",
            "tagline": "Test tagline",
            "strategic_narrative": "This is strategic",
            "campaign_theme": "Theme",
            "audience_segmentation": {"primary": "Gen-Z", "secondary": "Millennials", "tertiary": "Gen-X"},
            "channel_mix": [{"channel": "TikTok", "rationale": "High reach", "competitor_gap": "Gap"}],
            "message_architecture": {"master_message": "Message", "channel_adaptations": {"TikTok": "TikTok version"}},
            "campaign_phasing": {"awareness": "Phase 1", "engagement": "Phase 2", "conversion": "Phase 3"},
            "tone_board": {"adjectives": ["adj1", "adj2", "adj3", "adj4", "adj5"], "visual_direction": "Modern"},
            "risk_flags": {"legal": None, "regulatory": None, "sensitivity": None},
            "mandate_fit_score": "not a number",  # Invalid type
            "gap_exploitation_score": 8,
        }
        errors = validator.validate_schema(campaign)
        assert len(errors) > 0


class TestCampaignGeneration:
    """Test campaign generation function."""

    @pytest.mark.asyncio
    async def test_generate_campaign_returns_dict(self):
        """Generate campaign should return a dict."""
        from backend.app.agents.campaign_strategist import generate_campaign

        mandate = {
            "campaign_name": "Test Campaign",
            "objective": "Increase brand awareness",
            "target_audience": "Gen-Z",
            "budget": {"total_amount": 100000, "currency": "USD"},
            "geography": {"regions": ["North America"], "markets": ["US"], "country_list": ["US"]},
            "timeline": "Q2 2026 (12 weeks)",
            "brand_guidelines": {"tone": "authentic", "voice": "conversational"},
        }

        ci_report = {
            "competitors": [{"name": "Competitor A", "confidence_score": 95, "channels": {}, "messaging_themes": []}],
            "whitespace_opportunities": {
                "untapped_channels": ["TikTok", "Discord"],
                "messaging_gaps": ["Authenticity"],
                "geographic_gaps": ["Tech hubs"],
            },
        }

        with patch("backend.app.agents.campaign_strategist.AsyncAnthropic") as mock_anthropic:
            mock_client = AsyncMock()
            mock_anthropic.return_value = mock_client

            mock_message = MagicMock()
            mock_message.content = [
                MagicMock(
                    text='{"name": "Test", "tagline": "Test", "strategic_narrative": "Test", "campaign_theme": "Test", "audience_segmentation": {"primary": "Gen-Z", "secondary": "Millennials", "tertiary": "Gen-X"}, "channel_mix": [{"channel": "TikTok", "rationale": "High", "competitor_gap": "Gap"}], "message_architecture": {"master_message": "Test", "channel_adaptations": {"TikTok": "Test"}}, "campaign_phasing": {"awareness": "A", "engagement": "E", "conversion": "C"}, "tone_board": {"adjectives": ["a", "b", "c", "d", "e"], "visual_direction": "V"}, "risk_flags": {"legal": null, "regulatory": null, "sensitivity": null}, "mandate_fit_score": 9, "gap_exploitation_score": 8}'
                )
            ]
            mock_client.messages.create = AsyncMock(return_value=mock_message)

            result = await generate_campaign(mandate, ci_report, 1)

            assert result is not None
            assert isinstance(result, dict)
            assert "name" in result
            assert "risk_flags" in result

    @pytest.mark.asyncio
    async def test_generate_campaign_returns_none_on_parse_error(self):
        """Generate campaign should return None on JSON parse error."""
        from backend.app.agents.campaign_strategist import generate_campaign

        mandate = {
            "campaign_name": "Test",
            "objective": "Test",
            "target_audience": "Test",
            "budget": {"total_amount": 50000, "currency": "USD"},
            "geography": {"regions": ["US"], "markets": ["NYC"], "country_list": ["US"]},
            "timeline": "8 weeks",
            "brand_guidelines": {"tone": "professional"},
        }

        ci_report = {
            "competitors": [],
            "whitespace_opportunities": {
                "untapped_channels": ["LinkedIn"],
                "messaging_gaps": ["B2B"],
                "geographic_gaps": ["West"],
            },
        }

        with patch("backend.app.agents.campaign_strategist.AsyncAnthropic") as mock_anthropic:
            mock_client = AsyncMock()
            mock_anthropic.return_value = mock_client

            mock_message = MagicMock()
            mock_message.content = [MagicMock(text="Invalid JSON")]
            mock_client.messages.create = AsyncMock(return_value=mock_message)

            result = await generate_campaign(mandate, ci_report, 1)

            assert result is None


@pytest.mark.asyncio
async def test_campaign_strategist_agent_returns_3_campaigns():
    """Orchestrator should generate 3 campaign concepts."""
    mandate = {
        "campaign_name": "Test Campaign",
        "objective": "Increase brand awareness",
        "target_audience": "Gen-Z",
        "budget": {"total_amount": 100000, "currency": "USD"},
        "geography": {"regions": ["North America"], "markets": ["US"], "country_list": ["US"]},
        "timeline": "Q2 2026 (12 weeks)",
        "brand_guidelines": {"tone": "authentic", "voice": "conversational"},
    }

    ci_report = {
        "competitors": [{"name": "Competitor A", "confidence_score": 95, "channels": {}, "messaging_themes": []}],
        "whitespace_opportunities": {
            "untapped_channels": ["TikTok", "Discord"],
            "messaging_gaps": ["Authenticity"],
            "geographic_gaps": ["Tech hubs"],
        },
    }

    result = await campaign_strategist_agent(mandate, ci_report)

    assert "campaigns" in result
    assert "validation_errors" in result
    assert "regeneration_log" in result
    assert isinstance(result["campaigns"], list)
    assert len(result["campaigns"]) <= 3


@pytest.mark.asyncio
async def test_campaign_strategist_validates_output():
    """Orchestrator should validate all campaigns and report errors."""
    mandate = {
        "campaign_name": "Test",
        "objective": "Test objective",
        "target_audience": "Test audience",
        "budget": {"total_amount": 50000, "currency": "USD"},
        "geography": {"regions": ["US"], "markets": ["NYC"], "country_list": ["US"]},
        "timeline": "8 weeks",
        "brand_guidelines": {"tone": "professional"},
    }

    ci_report = {
        "competitors": [],
        "whitespace_opportunities": {
            "untapped_channels": ["LinkedIn"],
            "messaging_gaps": ["B2B focus"],
            "geographic_gaps": ["West Coast"],
        },
    }

    result = await campaign_strategist_agent(mandate, ci_report)

    assert "validation_errors" in result
    assert isinstance(result["validation_errors"], list)


@pytest.mark.asyncio
async def test_campaign_strategist_tracks_regenerations():
    """Orchestrator should log regeneration attempts."""
    mandate = {
        "campaign_name": "Test",
        "objective": "Test objective",
        "target_audience": "Test audience",
        "budget": {"total_amount": 50000, "currency": "USD"},
        "geography": {"regions": ["US"], "markets": ["NYC"], "country_list": ["US"]},
        "timeline": "8 weeks",
        "brand_guidelines": {"tone": "professional"},
    }

    ci_report = {
        "competitors": [],
        "whitespace_opportunities": {
            "untapped_channels": ["LinkedIn"],
            "messaging_gaps": ["B2B focus"],
            "geographic_gaps": ["West Coast"],
        },
    }

    result = await campaign_strategist_agent(mandate, ci_report)

    assert "regeneration_log" in result
    assert isinstance(result["regeneration_log"], list)


@pytest.mark.asyncio
async def test_campaign_strategist_agent_end_to_end(mock_anthropic_response):
    """End-to-end test: generate 3 campaigns with mocked API."""
    mandate = {
        "campaign_name": "Q2 Awareness",
        "objective": "Increase brand awareness in Gen-Z",
        "target_audience": "Gen-Z (16-24)",
        "budget": {"total_amount": 100000, "currency": "USD"},
        "geography": {"regions": ["North America"], "markets": ["US"], "country_list": ["US"]},
        "timeline": "Q2 2026 (12 weeks)",
        "brand_guidelines": {"tone": "authentic", "voice": "conversational"}
    }

    ci_report = {
        "competitors": [
            {
                "name": "Competitor A",
                "confidence_score": 95,
                "channels": {"Instagram": {"presence": True}},
                "messaging_themes": ["Corporate"]
            }
        ],
        "whitespace_opportunities": {
            "untapped_channels": ["TikTok", "Discord", "Twitch"],
            "messaging_gaps": ["Authenticity", "Gen-Z voice", "Creator focus"],
            "geographic_gaps": ["Tech hubs", "College towns"]
        }
    }

    with patch("backend.app.agents.campaign_strategist.AsyncAnthropic") as mock_anthropic:
        mock_client = AsyncMock()
        mock_anthropic.return_value = mock_client

        # Mock messages.create to return valid JSON responses for all 3 campaigns
        async def mock_create(**kwargs):
            mock_message = AsyncMock()
            # Determine which campaign this is by checking the prompt
            campaign_num = 1
            prompt_content = kwargs.get("messages", [{}])[0].get("content", "")
            if "campaign #2" in prompt_content.lower():
                campaign_num = 2
            elif "campaign #3" in prompt_content.lower():
                campaign_num = 3

            mock_message.content = [AsyncMock(text=mock_anthropic_response(campaign_num))]
            return mock_message

        mock_client.messages.create = mock_create

        # Execute the agent
        result = await campaign_strategist_agent(mandate, ci_report)

        # Verify structure
        assert "campaigns" in result
        assert "validation_errors" in result
        assert "regeneration_log" in result

        # Verify we got campaigns
        assert len(result["campaigns"]) > 0
        assert len(result["campaigns"]) <= 3

        # Verify first campaign structure
        first = result["campaigns"][0]
        assert first["name"] == "Campaign #1"
        assert first["tagline"] == "Campaign tagline #1"
        assert first["mandate_fit_score"] in range(1, 11)
        assert first["gap_exploitation_score"] in range(1, 11)
        assert len(first["tone_board"]["adjectives"]) == 5
        assert first["risk_flags"]["legal"] is None
