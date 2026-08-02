from __future__ import annotations

import requests
from typing import List

from backend.app.models.agents import ResearchOutput


def web_search_summary(query: str, max_results: int = 3) -> List[str]:
    """Do a lightweight DuckDuckGo HTML search and return link titles (best-effort)."""
    try:
        resp = requests.get("https://html.duckduckgo.com/html/", params={"q": query}, timeout=6)
        text = resp.text
        # crude parsing for hrefs
        results: List[str] = []
        parts = text.split("<a rel='nofollow' class='result__a' href='")
        for p in parts[1 : max_results + 1]:
            title = p.split("\">", 1)[-1].split("</a>", 1)[0]
            results.append(title)
        return results
    except Exception:
        return []


def research_for_framework(framework: str) -> ResearchOutput:
    best = [
        f"Use dependency injection patterns with {framework} to keep handlers thin.",
        "Prefer async database sessions when possible for throughput.",
        "Keep authentication secrets out of source; use env vars and secrets manager.",
    ]
    refs = web_search_summary(framework + " official docs") or [f"{framework} docs"]
    return ResearchOutput(framework=framework, best_practices=best, references=refs)
