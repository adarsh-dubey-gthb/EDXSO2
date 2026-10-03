"""
Robust web fetcher with connection pooling, retries, and Indian government portal SSL tolerance.
"""

import requests
import urllib3
import time
from typing import Optional, Tuple, Any
from bs4 import BeautifulSoup

# Suppress insecure request warnings caused by self-signed / custom Gov CA certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive"
}

import hashlib
from pathlib import Path

CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "web_cache"

class WebFetcher:
    def __init__(self, timeout: Any = (4, 6), max_retries: int = 1, use_cache: bool = True):
        self.timeout = timeout
        self.max_retries = max_retries
        self.use_cache = use_cache
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        
    def _get_cache_path(self, url: str) -> Path:
        url_hash = hashlib.md5(url.encode("utf-8")).hexdigest()
        return CACHE_DIR / f"{url_hash}.html"

    def fetch(self, url: str) -> Tuple[int, str, Optional[str]]:
        """
        Fetches the URL content with automated HTTP caching and retry resilience.
        Returns: (status_code, html_content_or_error, redirected_final_url)
        """
        cache_file = self._get_cache_path(url)
        
        # 1. Try live fetch
        for attempt in range(self.max_retries + 1):
            try:
                # verify=False is required for certain .gov.in domains using India PKI roots
                response = self.session.get(
                    url, 
                    timeout=self.timeout, 
                    verify=False,
                    allow_redirects=True
                )
                if response.status_code == 200 and response.text:
                    if self.use_cache:
                        try:
                            cache_file.write_text(response.text, encoding="utf-8")
                        except Exception:
                            pass
                    return response.status_code, response.text, str(response.url)
            except requests.exceptions.RequestException as e:
                if attempt == self.max_retries:
                    # 2. On network failure, fall back to cached HTML if available
                    if self.use_cache and cache_file.exists():
                        try:
                            cached_html = cache_file.read_text(encoding="utf-8")
                            return 200, cached_html, url
                        except Exception:
                            pass
                    return 0, f"Fetch Error: {str(e)}", None
                time.sleep(0.5)

        # 3. Fallback to cache if non-200
        if self.use_cache and cache_file.exists():
            try:
                cached_html = cache_file.read_text(encoding="utf-8")
                return 200, cached_html, url
            except Exception:
                pass

        return 0, "Max retries exceeded", None

    def extract_text(self, html: str) -> str:
        """Parses HTML and extracts clean normalized visible text."""
        if not html:
            return ""
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript", "header", "footer", "svg"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        # Normalize whitespace
        return " ".join(text.split())
