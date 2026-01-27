import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any

import requests
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional, Iterable


class WebsiteScraper:
    """
    Production-grade website crawler with semantic text extraction
    and token-aware truncation.
    """

    # ---------- Defaults ----------
    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (compatible; CompanyScraper/1.0)"
    }

    DEFAULT_KEYWORDS = {
        "about": ["about", "company", "who-we-are"],
        "contact": ["contact", "get-in-touch", "reach-us"],
        "mission": ["mission", "vision", "values", "purpose"],
    }

    DEFAULT_SEMANTIC_KEYWORDS = (
        "mission",
        "vision",
        "we are",
        "we help",
        "we provide",
        "our goal",
        "our purpose",
        "specialize",
        "focused on",
        "committed to",
        "leading",
    )

    SENTENCE_SPLIT_REGEX = re.compile(r"(?<=[.!?])\s+")

    # ---------- Init ----------
    def __init__(
        self,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 10,
        max_workers: int = 8,
        link_keywords: Optional[Dict[str, List[str]]] = None,
        enable_semantic_extraction: bool = True,
        max_tokens: int = 100,
        semantic_keywords: Optional[Iterable[str]] = None,
    ):
        self.headers = headers or self.DEFAULT_HEADERS
        self.timeout = timeout
        self.max_workers = max_workers
        self.link_keywords = link_keywords or self.DEFAULT_KEYWORDS

        self.enable_semantic_extraction = enable_semantic_extraction
        self.max_tokens = max_tokens
        self.semantic_keywords = semantic_keywords or self.DEFAULT_SEMANTIC_KEYWORDS

    # ---------- HTTP ----------
    def _fetch(self, url: str) -> BeautifulSoup:
        resp = requests.get(
            url,
            headers=self.headers,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")

    # ---------- Text extraction ----------
    @staticmethod
    def _extract_visible_text(soup: BeautifulSoup) -> str:
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        text = soup.get_text(separator=" ")
        return " ".join(text.split())

    # ---------- Token truncation ----------
    @staticmethod
    def _truncate_to_tokens(text: str, max_tokens: int) -> str:
        if not text:
            return ""

        max_chars = max_tokens * 4  # ~4 chars per token
        text = text.strip()

        if len(text) <= max_chars:
            return text

        truncated = text[:max_chars]
        last_space = truncated.rfind(" ")
        return truncated[:last_space] if last_space > 0 else truncated

    # ---------- Semantic extraction ----------
    def _extract_semantic_sentences(self, text: str) -> str:
        if not text:
            return ""

        sentences = self.SENTENCE_SPLIT_REGEX.split(text)
        char_budget = self.max_tokens * 4
        current_chars = 0
        selected = []

        for sentence in sentences:
            sentence = sentence.strip()
            lower = sentence.lower()

            if any(k in lower for k in self.semantic_keywords):
                if current_chars + len(sentence) > char_budget:
                    break

                selected.append(sentence)
                current_chars += len(sentence)

        if selected:
            return " ".join(selected)

        # fallback: first sentence truncated
        return self._truncate_to_tokens(sentences[0], self.max_tokens) if sentences else ""

    # ---------- Normalization ----------
    def _normalize_text(self, text: str) -> str:
        if not self.enable_semantic_extraction:
            return self._truncate_to_tokens(text, self.max_tokens)

        return self._extract_semantic_sentences(text)

    # ---------- Link discovery ----------
    def _find_relevant_links(
        self, base_url: str, soup: BeautifulSoup
    ) -> Dict[str, List[str]]:
        links = {key: [] for key in self.link_keywords}

        for a in soup.find_all("a", href=True):
            href = a["href"].lower()
            full_url = urljoin(base_url, a["href"])

            for category, keywords in self.link_keywords.items():
                if any(k in href for k in keywords):
                    links[category].append(full_url)

        # de-duplicate while preserving order
        return {k: list(dict.fromkeys(v)) for k, v in links.items()}

    # ---------- Page scraping ----------
    def _scrape_page(self, url: str) -> str:
        soup = self._fetch(url)
        raw_text = self._extract_visible_text(soup)
        return self._normalize_text(raw_text)

    # ---------- Single site scrape ----------
    def scrape(self, url: str) -> Dict[str, Any]:
        base_url = url.rstrip("/")

        result = {
            "url": base_url,
            "homepage_text": "",
            "about": "",
            "contact": "",
            "mission": "",
        }

        try:
            homepage_soup = self._fetch(base_url)
            homepage_text = self._extract_visible_text(homepage_soup)
            result["homepage_text"] = self._normalize_text(homepage_text)

            links = self._find_relevant_links(base_url, homepage_soup)

            for section, urls in links.items():
                if not urls:
                    continue

                try:
                    result[section] = self._scrape_page(urls[0])
                except Exception:
                    result[section] = ""

        except Exception:
            # Fail closed but safe
            pass

        return result

    # ---------- Concurrent scraping ----------
    def scrape_many(self, urls: List[str]) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self.scrape, url): url
                for url in urls
            }

            for future in as_completed(futures):
                try:
                    results.append(future.result())
                except Exception:
                    pass

        return results
