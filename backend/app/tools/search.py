from __future__ import annotations

import html
import re
from dataclasses import dataclass
from urllib.parse import urljoin

import requests

from backend.app.core.config import settings


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str = ""


class SearchTool:
    def search(self, query: str, max_results: int = 3) -> list[SearchResult]:
        if not query.strip():
            return []

        try:
            response = requests.get(
                "https://html.duckduckgo.com/html/",
                params={"q": query},
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=settings.search_timeout_seconds,
            )
            response.raise_for_status()
        except Exception:
            return []

        html_text = response.text
        matches = re.findall(
            r'<a[^>]+class="result__a"[^>]+href="(?P<url>[^"]+)"[^>]*>(?P<title>.*?)</a>',
            html_text,
            flags=re.IGNORECASE | re.DOTALL,
        )
        snippets = re.findall(
            r'<a[^>]+class="result__snippet"[^>]*>(?P<snippet>.*?)</a>',
            html_text,
            flags=re.IGNORECASE | re.DOTALL,
        )

        results: list[SearchResult] = []
        for index, (url, title) in enumerate(matches[:max_results]):
            snippet = snippets[index] if index < len(snippets) else ""
            results.append(
                SearchResult(
                    title=html.unescape(re.sub(r"<.*?>", "", title)).strip(),
                    url=urljoin("https://duckduckgo.com", html.unescape(url)),
                    snippet=html.unescape(re.sub(r"<.*?>", "", snippet)).strip(),
                )
            )
        return results