"""Tolerant JSON parsing for real LLM responses.

Production models frequently wrap JSON in ```json fences or add stray prose despite
explicit instructions, which breaks a bare ``json.loads``. ``extract_json`` is a
drop-in replacement: it strips fences, then falls back to the outermost ``{...}`` or
``[...]`` block. It raises ``json.JSONDecodeError`` when nothing parses, so existing
``except json.JSONDecodeError`` handlers keep working unchanged.
"""

import json
import re
from typing import Any

_OPEN_FENCE = re.compile(r"^```[a-zA-Z]*\s*")
_CLOSE_FENCE = re.compile(r"\s*```$")


def extract_json(text: str) -> Any:
    """Parse JSON (object or array) from a possibly-fenced LLM response.

    Raises json.JSONDecodeError if no JSON can be recovered.
    """
    if not text or not text.strip():
        raise json.JSONDecodeError("empty response", text or "", 0)
    s = text.strip()
    if s.startswith("```"):
        s = _OPEN_FENCE.sub("", s)
        s = _CLOSE_FENCE.sub("", s).strip()
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        match = re.search(r"(\{.*\}|\[.*\])", s, re.DOTALL)
        if match:
            return json.loads(match.group(0))  # may raise; caller's handler catches
        raise
