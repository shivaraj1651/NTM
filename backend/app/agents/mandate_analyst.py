"""
Mandate Analyst Agent (AGT-01).

Validates mandates for completeness and contradictions, produces structured summary cards.
"""

from typing import Dict, List, Any


class MandateValidator:
    """
    Validates mandate dict for required fields and basic type checks.

    Required fields (17 total):
    - Top-level: approval_date, mandated_by, version, status (4)
    - campaign_concept: id, name, objective, description, target_audience, timeline (6)
    - budget: total_amount, currency, allocation_strategy, contingency_reserve (4)
    - geography: regions, markets, country_list (3)
    """

    REQUIRED_FIELDS = {
        "top_level": ["approval_date", "mandated_by", "version", "status"],
        "campaign_concept": ["id", "name", "objective", "description", "target_audience", "timeline"],
        "budget": ["total_amount", "currency", "allocation_strategy", "contingency_reserve"],
        "geography": ["regions", "markets", "country_list"]
    }

    def __init__(self):
        """Initialize validator."""
        self.total_required = sum(len(v) for v in self.REQUIRED_FIELDS.values())

    def validate(self, mandate: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate mandate for required fields.

        Args:
            mandate: Raw mandate dict

        Returns:
            Dict with is_complete, missing_fields, field_count, field_total
        """
        missing_fields: List[str] = []
        field_count = 0

        # Check top-level fields
        for field in self.REQUIRED_FIELDS["top_level"]:
            if field in mandate and mandate[field] is not None:
                field_count += 1
            else:
                missing_fields.append(field)

        # Check nested sections
        for section, fields in self.REQUIRED_FIELDS.items():
            if section == "top_level":
                continue

            if section not in mandate or mandate[section] is None:
                # Entire section missing
                for field in fields:
                    missing_fields.append(f"{section}.{field}")
            else:
                section_data = mandate[section]
                for field in fields:
                    if field in section_data and section_data[field] is not None:
                        field_count += 1
                    else:
                        missing_fields.append(f"{section}.{field}")

        return {
            "is_complete": len(missing_fields) == 0,
            "missing_fields": missing_fields,
            "field_count": field_count,
            "field_total": self.total_required
        }
