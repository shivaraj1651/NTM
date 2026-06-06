"""Media Planner Agent (AGT-04).

Transforms approved campaign concepts and budgets into detailed Activation Master Plans.
Uses LLM-driven intelligence for context-aware planning, then applies a top-down
budget allocation framework: phases → channels → geographies.
"""

import logging
from datetime import date, timedelta
from typing import Any

from pydantic import ValidationError

from backend.app.schemas.media_plan import Activation, AudienceSegmentEnum, ChannelEnum, PhaseEnum

logger = logging.getLogger(__name__)


# ── LLM Intelligence Layer ────────────────────────────────────────────────────

def _generate_plan_intelligence(
    campaign_concept: dict[str, Any],
    budget_envelope: dict[str, Any],
    mandate_geography: dict[str, Any],
    mandate_context: dict[str, Any],
) -> dict[str, Any]:
    """
    Return objective-aware planning parameters using deterministic logic.

    Uses pre-calibrated phase splits, CPM-based audience estimates, and
    channel-specific format/placement defaults. No LLM call — plan generation
    is instant and fully deterministic.
    """
    objective = mandate_context.get("objective", "awareness").lower()
    markets   = (mandate_geography.get("markets") or
                 mandate_geography.get("country_list") or
                 mandate_geography.get("countries") or [])
    channels  = [c.get("channel", "") for c in campaign_concept.get("channel_mix", [])]

    phase_splits = {
        "awareness":     {"Awareness": 0.55, "Engagement": 0.35, "Conversion": 0.10},
        "consideration": {"Awareness": 0.35, "Engagement": 0.45, "Conversion": 0.20},
        "conversion":    {"Awareness": 0.20, "Engagement": 0.35, "Conversion": 0.45},
        "loyalty":       {"Awareness": 0.20, "Engagement": 0.50, "Conversion": 0.30},
        "engagement":    {"Awareness": 0.30, "Engagement": 0.55, "Conversion": 0.15},
    }

    channel_formats: dict[str, dict[str, str]] = {
        "TikTok":     {"format": "15-second vertical video", "placement": "For You feed"},
        "Instagram":  {"format": "Story + Reel carousel", "placement": "Stories & Explore"},
        "Facebook":   {"format": "Single-image or video ad", "placement": "News Feed"},
        "YouTube":    {"format": "15-second skippable in-stream", "placement": "Pre-roll"},
        "Google Ads": {"format": "Responsive search ad", "placement": "Search & Display"},
        "LinkedIn":   {"format": "Sponsored content post", "placement": "LinkedIn Feed"},
        "Twitter":    {"format": "Promoted tweet with image", "placement": "Timeline"},
        "Snapchat":   {"format": "Full-screen Snap ad", "placement": "Between Stories"},
        "Email":      {"format": "HTML newsletter", "placement": "Inbox"},
        "TV":         {"format": "30-second TVC", "placement": "Prime time"},
        "Radio":      {"format": "30-second audio spot", "placement": "Drive time"},
        "Print":      {"format": "Full-page display ad", "placement": "Magazine/newspaper"},
        "OOH":        {"format": "Static billboard", "placement": "High-traffic outdoor"},
        "WhatsApp":   {"format": "Click-to-chat ad", "placement": "Status"},
        "Influencer": {"format": "Sponsored post/story", "placement": "Creator profile"},
    }

    return {
        "phase_split": phase_splits.get(objective, {"Awareness": 0.40, "Engagement": 0.40, "Conversion": 0.20}),
        "audience_size_per_market": {m: 2_000_000 for m in markets},
        "channel_context": {
            ch: {
                "format":           channel_formats.get(ch, {}).get("format", f"{ch} ad"),
                "placement":        channel_formats.get(ch, {}).get("placement", f"{ch} feed"),
                "audience_segment": "Primary",
                "rationale":        f"Standard {objective} placement on {ch}.",
            }
            for ch in channels
        },
        "strategic_rationale": (
            f"Objective-calibrated {objective} plan across {len(channels)} channel(s) "
            f"in {len(markets)} market(s)."
        ),
    }


# ── Budget Allocator ──────────────────────────────────────────────────────────

class BudgetAllocator:
    """Allocates budget across phases, channels, and geographies."""

    def allocate_by_phase(
        self,
        total_budget: float,
        phase_split: dict[str, float] | None = None,
    ) -> dict[str, float]:
        """Allocate budget across phases using provided split ratios."""
        phase_split = phase_split or {
            "Awareness": 0.40,
            "Engagement": 0.40,
            "Conversion": 0.20,
        }
        return {phase: total_budget * ratio for phase, ratio in phase_split.items()}

    def allocate_by_channel(self, phase_budget: float, channels: list[dict[str, Any]]) -> dict[str, float]:
        """Allocate phase budget across channels by weight."""
        allocations = {}
        total_weight = sum(ch.get("weight", 1.0) for ch in channels) or 1.0
        for ch in channels:
            weight = ch.get("weight", 1.0)
            channel_name = ch["channel"]
            allocations[channel_name] = phase_budget * (weight / total_weight)
        return allocations

    def allocate_by_geography(self, channel_budget: float, geographies: list[str]) -> dict[str, float]:
        """Allocate channel budget equally across geographies."""
        per_geography = channel_budget / len(geographies) if geographies else 0.0
        return {geo: per_geography for geo in geographies}

    def calculate_contingency(self, total_spend: float, pct: float = 0.10) -> float:
        return total_spend * pct


# ── Activation Generator ──────────────────────────────────────────────────────

class ActivationGenerator:
    """Generates activation details with reach, cost, frequency, and CPM calculations."""

    CHANNEL_CPM_RATES = {
        "TikTok": 5.0,
        "Instagram": 8.0,
        "Facebook": 7.0,
        "YouTube": 10.0,
        "TV": 20.0,
        "Email": 0.50,
        "Radio": 12.0,
        "Print": 15.0,
        "Google Ads": 12.0,
        "LinkedIn": 14.0,
        "Twitter": 6.0,
        "Snapchat": 4.0,
        "OOH": 9.0,
        "WhatsApp": 1.0,
        "Influencer": 18.0,
    }

    PHASE_PENETRATION = {
        "Awareness": 0.60,
        "Engagement": 0.30,
        "Conversion": 0.10,
    }

    PHASE_FREQUENCY = {
        "Awareness": "3x daily",
        "Engagement": "2x daily",
        "Conversion": "1x daily",
    }

    def calculate_reach(self, audience_size: int, penetration_pct: float) -> int:
        return int(audience_size * penetration_pct)

    def calculate_cost(self, reach: int, cpm: float) -> float:
        return (reach / 1000.0) * cpm

    def get_frequency_for_phase(self, phase: str) -> str:
        return self.PHASE_FREQUENCY.get(phase, "1x daily")

    def get_cpm_for_channel(self, channel_name: str) -> float:
        return self.CHANNEL_CPM_RATES.get(channel_name, 10.0)

    def get_penetration_for_phase(self, phase: str) -> float:
        return self.PHASE_PENETRATION.get(phase, 0.0)


# ── Offline Constraint Handler ────────────────────────────────────────────────

class OfflineConstraintHandler:
    """Manages lead time constraints for offline channels."""

    OFFLINE_LEAD_TIMES = {
        "TV": 28, "Print": 14, "Cinema": 21,
        "Radio": 10, "Events": 14, "DirectMail": 14, "OOH": 7,
    }
    OFFLINE_CHANNELS = set(OFFLINE_LEAD_TIMES.keys())

    def is_offline(self, channel_name: str) -> bool:
        return channel_name in self.OFFLINE_CHANNELS

    def get_lead_time_days(self, channel_name: str) -> int:
        return self.OFFLINE_LEAD_TIMES.get(channel_name, 0)

    def calculate_scheduled_date(self, channel_name: str, phase_start: date) -> date:
        return phase_start - timedelta(days=self.get_lead_time_days(channel_name))

    def get_offline_constraints_note(self, channel_name: str) -> str | None:
        if not self.is_offline(channel_name):
            return None
        lead_time = self.get_lead_time_days(channel_name)
        if lead_time == 0:
            return None
        weeks = lead_time // 7
        if lead_time % 7 == 0 and weeks > 0:
            return f"Requires {weeks} week{'s' if weeks > 1 else ''} lead time"
        return f"Requires {lead_time} days lead time"


# ── Activation Validator ──────────────────────────────────────────────────────

class ActivationValidator:
    """Validates Activation objects against the Pydantic schema."""

    def validate_schema(self, activation_dict: dict) -> list[str]:
        try:
            Activation(**activation_dict)
            return []
        except ValidationError as e:
            return [
                f"Field '{'.'.join(str(loc) for loc in err['loc'])}': {err['msg']}"
                for err in e.errors()
            ]


# ── Segment Mapper ────────────────────────────────────────────────────────────

_SEGMENT_MAP = {
    "Primary":   AudienceSegmentEnum.PRIMARY,
    "Secondary": AudienceSegmentEnum.SECONDARY,
    "Tertiary":  AudienceSegmentEnum.TERTIARY,
}


def _resolve_channel_enum(channel_name: str) -> ChannelEnum:
    name = channel_name.lower()
    if any(k in name for k in ("facebook", "instagram", "tiktok", "snapchat", "twitter", "linkedin")):
        return ChannelEnum.SOCIAL
    if "email" in name:
        return ChannelEnum.EMAIL
    if any(k in name for k in ("youtube", "display", "banner")):
        return ChannelEnum.DISPLAY
    if "tv" in name:
        return ChannelEnum.TV
    if "radio" in name:
        return ChannelEnum.RADIO
    if "print" in name:
        return ChannelEnum.PRINT
    return ChannelEnum.SOCIAL


# ── Orchestrator ──────────────────────────────────────────────────────────────

async def media_planner_agent(
    campaign_concept: dict[str, Any],
    budget_envelope: dict[str, Any],
    mandate_geography: dict[str, Any],
    mandate_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Main orchestrator: LLM-intelligence → allocation → activation generation → validation.

    Args:
        campaign_concept: Dict with channel_mix, campaign_phasing, tone_board, message_architecture
        budget_envelope: Dict with total_budget, currency, contingency_pct
        mandate_geography: Dict with regions, markets, countries
        mandate_context: Optional dict with objective, description, target_audience

    Returns:
        Dict with activations, budget_summary, validation_errors, allocation_log, status
    """
    allocator        = BudgetAllocator()
    generator        = ActivationGenerator()
    constraint_handler = OfflineConstraintHandler()
    validator        = ActivationValidator()

    # ── Step 0: planning intelligence (deterministic, instant) ───────────────
    ctx = mandate_context or {}
    intelligence = _generate_plan_intelligence(
        campaign_concept, budget_envelope, mandate_geography, ctx
    )

    phase_split           = intelligence.get("phase_split", {"Awareness": 0.40, "Engagement": 0.40, "Conversion": 0.20})
    audience_size_map     = intelligence.get("audience_size_per_market", {})
    channel_ctx           = intelligence.get("channel_context", {})
    strategic_rationale   = intelligence.get("strategic_rationale", "")

    # ── Extract inputs ────────────────────────────────────────────────────────
    total_budget    = budget_envelope.get("total_budget", 100000.0)
    currency        = budget_envelope.get("currency", "USD")
    contingency_pct = budget_envelope.get("contingency_pct", 0.10)
    # geography: real mandate uses country_list / countries; legacy uses markets
    markets         = (mandate_geography.get("markets") or
                       mandate_geography.get("country_list") or
                       mandate_geography.get("countries") or [])
    channels        = campaign_concept.get("channel_mix", [])
    campaign_phasing = campaign_concept.get("campaign_phasing", {})
    tone_board      = campaign_concept.get("tone_board", {})
    message_architecture = campaign_concept.get("message_architecture", {})

    activations           = []
    validation_errors     = []
    allocation_log        = [f"Strategic rationale: {strategic_rationale}"]
    total_spent           = 0.0
    channel_activation_counts   = {}
    phase_breakdown_tracking    = {}
    channel_breakdown_tracking  = {}

    # ── Phase allocation ──────────────────────────────────────────────────────
    phase_budgets = allocator.allocate_by_phase(total_budget, phase_split)
    allocation_log.append(
        "Phase budget allocation (objective-driven): "
        + ", ".join(f"{p}={v:.2f}" for p, v in phase_budgets.items())
    )

    # ── Per-phase planning ────────────────────────────────────────────────────
    for phase_name, phase_budget in phase_budgets.items():
        phase_breakdown_tracking[phase_name] = {
            "allocated": phase_budget, "spent": 0.0, "remaining": phase_budget
        }

        channel_budgets = allocator.allocate_by_channel(phase_budget, channels)
        allocation_log.append(f"{phase_name} channel allocation: {channel_budgets}")

        for channel_dict in channels:
            channel_name   = channel_dict.get("channel", "Unknown")
            channel_budget = channel_budgets.get(channel_name, 0.0)
            ch_intel       = channel_ctx.get(channel_name, {})

            channel_activation_counts.setdefault(channel_name, 0)
            channel_breakdown_tracking.setdefault(channel_name, {
                "allocated": 0.0, "spent": 0.0, "activations_count": 0
            })
            channel_breakdown_tracking[channel_name]["allocated"] += channel_budget

            # campaign_phasing values may be strings ("Weeks 1-2: teaser...") or
            # dicts with a "start" key — tolerate both shapes.
            _phase_val   = campaign_phasing.get(phase_name, {})
            if isinstance(_phase_val, dict):
                _start = _phase_val.get("start")
                try:
                    from datetime import datetime as _dt
                    phase_start = _dt.fromisoformat(str(_start)).date() if _start else date.today()
                except Exception:
                    phase_start = date.today()
            else:
                phase_start = date.today()

            for market in markets:
                market_budget  = channel_budget / len(markets) if markets else 0.0

                # Audience size from LLM intelligence (fallback 2M)
                audience_size  = audience_size_map.get(market, 2_000_000)
                penetration    = generator.get_penetration_for_phase(phase_name)
                estimated_reach = generator.calculate_reach(audience_size, penetration)

                cpm            = generator.get_cpm_for_channel(channel_name)
                estimated_cost = min(generator.calculate_cost(estimated_reach, cpm), market_budget)

                channel_enum   = _resolve_channel_enum(channel_name)
                scheduled_date = constraint_handler.calculate_scheduled_date(channel_name, phase_start)
                offline_constraints = constraint_handler.get_offline_constraints_note(channel_name)
                lead_time_days = constraint_handler.get_lead_time_days(channel_name)
                frequency      = generator.get_frequency_for_phase(phase_name)

                # LLM-driven format, placement, segment (fallbacks for unknown channels)
                fmt     = ch_intel.get("format") or f"{channel_name} {phase_name.lower()} ad"
                placement = ch_intel.get("placement") or f"{channel_name} feed"
                segment_str = ch_intel.get("audience_segment", "Primary")
                audience_segment = _SEGMENT_MAP.get(segment_str, AudienceSegmentEnum.PRIMARY)

                # Message version reference — real tone_board has adjectives not a "tone" key;
                # real message_architecture has master_message not "primary"
                _tb = tone_board if isinstance(tone_board, dict) else {}
                tone_str    = (_tb.get("tone") or
                               ", ".join(_tb.get("adjectives", [])) or
                               "professional")
                message_str = (message_architecture.get("master_message") or
                               message_architecture.get("primary") or
                               "brand message")
                message_version_ref = f"{channel_name} | {tone_str} | {message_str}"

                activation_dict = {
                    "channel_enum":      channel_enum,
                    "sub_channel":       channel_name,
                    "format":            fmt,
                    "geography":         market,
                    "placement":         placement,
                    "phase":             PhaseEnum(phase_name),
                    "scheduled_date":    scheduled_date,
                    "duration":          _campaign_duration_days(campaign_phasing, phase_name),
                    "frequency":         frequency,
                    "audience_segment":  audience_segment,
                    "estimated_reach":   estimated_reach,
                    "estimated_cpm":     cpm,
                    "cost_estimated":    estimated_cost,
                    "message_version_ref": message_version_ref,
                    "lead_time_days":    lead_time_days if lead_time_days > 0 else None,
                    "offline_constraints": offline_constraints,
                }

                errors = validator.validate_schema(activation_dict)
                if not errors:
                    activations.append(Activation(**activation_dict))
                    total_spent += estimated_cost
                    channel_activation_counts[channel_name] += 1
                    channel_breakdown_tracking[channel_name]["spent"] += estimated_cost
                    channel_breakdown_tracking[channel_name]["activations_count"] += 1
                    phase_breakdown_tracking[phase_name]["spent"] += estimated_cost
                else:
                    validation_errors.extend(errors)
                    allocation_log.append(f"Validation failed for {channel_name}/{market}/{phase_name}: {errors}")

    # ── Finalise ──────────────────────────────────────────────────────────────
    for phase_name in phase_breakdown_tracking:
        phase_breakdown_tracking[phase_name]["remaining"] = (
            phase_breakdown_tracking[phase_name]["allocated"]
            - phase_breakdown_tracking[phase_name]["spent"]
        )

    contingency_allocated = total_budget - sum(p["allocated"] for p in phase_breakdown_tracking.values())
    contingency_used      = allocator.calculate_contingency(total_spent, contingency_pct)

    budget_summary = {
        "total_budget":    total_budget,
        "currency":        currency,
        "phase_breakdown": phase_breakdown_tracking,
        "channel_breakdown": channel_breakdown_tracking,
        "contingency": {
            "allocated":  contingency_allocated,
            "used":       contingency_used,
            "remaining":  contingency_allocated - contingency_used,
        },
        "total_spent":    total_spent,
        "total_remaining": total_budget - total_spent,
        "utilization_pct": (total_spent / total_budget * 100) if total_budget > 0 else 0.0,
        "strategic_rationale": strategic_rationale,
    }

    status = "success" if not validation_errors else ("partial" if activations else "failed")
    logger.info(f"Media planner generated {len(activations)} activations with status={status}")

    return {
        "activations":       activations,
        "budget_summary":    budget_summary,
        "validation_errors": validation_errors,
        "allocation_log":    allocation_log,
        "status":            status,
    }


def _campaign_duration_days(campaign_phasing: dict[str, Any], phase_name: str) -> int:
    """Derive phase duration from phasing dates, default 14 days.

    Tolerates both dict shape ({"start":..., "end":...}) and string shape
    ("Weeks 1-2: teaser drops...") produced by real LLM campaign concepts.
    """
    phase_val = campaign_phasing.get(phase_name, {})
    if not isinstance(phase_val, dict):
        return 14  # string phasing — default duration
    start = phase_val.get("start")
    end   = phase_val.get("end")
    if start and end:
        try:
            if isinstance(start, str):
                from datetime import datetime
                start = datetime.fromisoformat(start).date()
            if isinstance(end, str):
                from datetime import datetime
                end = datetime.fromisoformat(end).date()
            return max(1, (end - start).days)
        except Exception:
            pass
    return 14
