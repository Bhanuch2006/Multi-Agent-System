from __future__ import annotations

import json
import re
from typing import Any


def extract_json_block(text: str) -> str:
    cleaned = text.strip()

    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("No JSON object found in model response")

    return cleaned[start : end + 1]


def parse_json_object(text: str) -> dict[str, Any]:
    return json.loads(extract_json_block(text))
