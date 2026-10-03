"""
Intelligent Discovery Engine — Open-Web Snowball Crawler.

Architecture:
  Tier 1 — Hardcoded seed portals (SEED_SOURCES): trusted starting points.
  Tier 2 — Persistent DB seeds (discovered_seeds table): domains found in previous runs,
            automatically reused as additional starting points so the crawl universe GROWS.
  Tier 3 — BFS multi-hop link traversal: follows outbound links from all seeds to
            completely new external domains never seen before.
  Tier 4 — Open-web DuckDuckGo search: discovers brand-new portals not linked from any
            known source, injecting them into Tier 2 for permanent retention.

Result: Each crawl run discovers new scholarship portals and websites beyond any predefined list.
        The crawler's known universe expands permanently with every run.
"""

from typing import List, Dict, Any, Set, Tuple
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import re
from crawler.fetcher import WebFetcher
from crawler.classifier import SourceClassifier
from config.seed_sources import SEED_SOURCES

SCHOLARSHIP_KEYWORDS = [
    # Core educational and student terms (no bare words like 'scheme' or 'grant')
    "scholarship", "fellowship", "stipend", "bursary", "tuition",
    "post-matric", "pre-matric", "higher-education", "free-education",
    "inspire-she", "inspire-fellowship", "pragati", "saksham", "swanath",
    "means-cum-merit", "merit-scholarship", "top-class-education",
    "research-fellowship", "jrf", "srf", "phd-fellowship", "doctoral",
    "girl-scholarship", "women-scientist", "chhatravritti", "vidyarthi",
    "ekalyan", "oasis", "mahadbt", "pmrf", "ongc-scholar",
    "student-scholarship", "national-scholarship", "education-grant"
]

# Topic queries for open-web search — strictly qualified with educational keywords
AUTONOMOUS_DISCOVERY_TOPICS = [

    # Central Government Portals & Schemes
    "National Scholarship Portal official portal scholarships.gov.in schemes students",
    "AICTE technical education scholarship Pragati Saksham scheme guidelines students",
    "Ministry of Education scholarship scheme post matric students site:gov.in",
    "Ministry of Social Justice post matric scholarship SC ST OBC students portal",
    "Ministry of Tribal Affairs higher education scholarship ST students portal",
    "Ministry of Minority Affairs post-matric scholarship students portal",
    # Science & Research Fellowships
    "Department of Science and Technology INSPIRE fellowship guidelines online-inspire.gov.in",
    "DST Women Scientist Scheme WOS-A fellowship students guidelines",
    "CSIR Junior Research Fellowship JRF NET exam fellowship guidelines csirhrdg.res.in",
    "ICMR Senior Research Fellowship biomedical research students fellowship",
    "Prime Minister Research Fellowship PMRF official portal IIT IISc pmrf.in",
    "UGC Junior Research Fellowship JRF fellowship guidelines students ugcnet",
    # Corporate CSR & Foundations
    "Reliance Foundation undergraduate postgraduate scholarship eligibility apply",
    "Tata Trusts higher education scholarship means merit students",
    "Infosys Foundation STEM Stars scholarship girl students engineering",
    "HDFC Parivartan scholarship program school college students",
    "Wipro Foundation higher education scholarship grant students",
    "Kotak Education Foundation scholarship meritorious 12th passed students",
    "Azim Premji Foundation education fellowship students India",
    "ONGC Foundation scholarship SC ST OBC college students",
    # State Portals
    "MahaDBT Maharashtra government scholarship portal post matric students",
    "UP scholarship portal scholarship.up.gov.in post matric students",
    "Bihar eKalyan post matric scholarship students official portal ekalyan.bih.nic.in",
    "Karnataka State Scholarship Portal SSP post matric students sw.kar.nic.in",
    "West Bengal OASIS scholarship oasis.gov.in post matric students",
    # Specialised
    "Scholarship for girl students engineering degree STEM India 2026",
    "PwD disability scholarship student higher education India 2026",
    "Means cum merit scholarship students site:gov.in",
]

IGNORE_EXTENSIONS = [
    ".jpg", ".jpeg", ".png", ".gif", ".css", ".js", ".zip", ".tar",
    ".mp4", ".mp3", ".pdf", ".doc", ".docx", ".xls", ".xlsx"
]

# Domains we will never crawl (aggregators, social media, CDNs, non-educational civic services)
BLOCKED_DOMAINS = {
    "buddy4study.com", "scholarshipsads.com", "shiksha.com", "collegedunia.com",
    "careers360.com", "jagranjosh.com", "sarkariresult.com", "embibe.com",
    "facebook.com", "twitter.com", "instagram.com", "youtube.com", "linkedin.com",
    "google.com", "cloudflare.com", "amazonaws.com", "googleapis.com",
    "wikipedia.org", "wikimedia.org",
    # Non-educational civic services
    "biharbhumi.bihar.gov.in", "tourism.bihar.gov.in", "serviceonline.bihar.gov.in",
    "transport.bihar.gov.in", "labour.bihar.gov.in",
}


class DiscoveryEngine:
    def __init__(self, fetcher: WebFetcher):
        self.fetcher = fetcher
        self.discovered_urls: Set[str] = set()

    # ──────────────────────────────────────────────────────────────────────
    # PRIMARY ENTRY POINT
    # ──────────────────────────────────────────────────────────────────────
    def discover_all_autonomous(
        self,
        max_links_per_seed: int = 10,
        depth: int = 3,
        enable_web_search: bool = True
    ) -> List[Dict[str, Any]]:
        """
        100% Fully Autonomous Open-Web Discovery.

        How it works (4-tier snowball system):
          Tier 1: Start from hardcoded seed portals.
          Tier 2: Load ALL previously discovered external domains from the DB
                  (these grew from previous crawl runs) and add them to the frontier.
          Tier 3: BFS multi-hop traversal follows outbound links to completely new
                  external domains, saves them persistently to the DB for future runs.
          Tier 4: DuckDuckGo open-web search discovers portals not linked from anything,
                  saves them too — so the universe keeps growing every single run.
        """
        from storage.database import load_discovered_seeds, save_discovered_seed, init_db
        init_db()

        all_candidates: List[Dict[str, Any]] = []
        seen_urls: Set[str] = set()

        # ── TIER 2: Load previously discovered seeds from DB ──────────────
        db_seeds = load_discovered_seeds()
        if db_seeds:
            print(f"  [FRONTIER EXPANSION] Loading {len(db_seeds)} previously discovered external seeds from DB...")

        # Build extended seed list = hardcoded + DB-discovered
        extended_seeds = list(SEED_SOURCES)
        known_seed_urls = {s["url"].lower().rstrip("/") for s in SEED_SOURCES}

        for ds in db_seeds:
            ds_url_norm = ds["url"].lower().rstrip("/")
            if ds_url_norm not in known_seed_urls:
                extended_seeds.append({
                    "url": ds["url"],
                    "name": ds.get("name") or ds["domain"],
                    "category": ds.get("source_type", "Central Government"),
                    "priority": "MEDIUM",
                    "is_authoritative": bool(ds.get("is_authoritative", False)),
                    "_from_db": True
                })
                known_seed_urls.add(ds_url_norm)

        print(f"  [FRONTIER] Total seed frontier: {len(extended_seeds)} portals "
              f"({len(SEED_SOURCES)} hardcoded + {len(db_seeds)} DB-discovered)")

        # ── TIER 1 + 3: BFS traversal across all seeds ────────────────────
        seed_candidates = self._bfs_discover(
            seeds=extended_seeds,
            max_links_per_seed=max_links_per_seed,
            depth=depth,
            save_new_domains=True   # Persist newly found external domains to DB
        )
        for c in seed_candidates:
            if c["url"] not in seen_urls:
                seen_urls.add(c["url"])
                all_candidates.append(c)

        # ── TIER 4: Open-web DuckDuckGo search for completely unknown portals
        if enable_web_search:
            import random
            # Select 3-4 diverse topics per crawl cycle to keep discovery fast and avoid rate limits
            selected_topics = random.sample(AUTONOMOUS_DISCOVERY_TOPICS, min(4, len(AUTONOMOUS_DISCOVERY_TOPICS)))
            print(f"  [WEB SEARCH] Running {len(selected_topics)} targeted open-web discovery queries...")
            new_domains_found = 0
            for topic in selected_topics:
                topic_candidates = self.discover_from_query(topic, max_results=4)
                for tc in topic_candidates:
                    url = tc["url"]
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)

                    parsed = urlparse(url)
                    domain = parsed.netloc.lower()
                    domain_root = re.sub(r'^www\.', '', domain)

                    # Verify positive educational relevance
                    cand_text = (tc.get("title", "") + " " + tc.get("snippet", "") + " " + url).lower()
                    is_edu = any(k in cand_text for k in [
                        "scholarship", "fellowship", "stipend", "student", "education", 
                        "post-matric", "pre-matric", "inspire", "pragati", "jrf", "srf", "phd", "chhatravritti"
                    ])

                    if (domain_root not in BLOCKED_DOMAINS 
                            and tc.get("is_authoritative") 
                            and tc.get("source_type") != "Non-Educational Government / Utility"
                            and is_edu):

                        seed_url = f"{parsed.scheme}://{domain}"
                        norm = seed_url.lower().rstrip("/")
                        if norm not in known_seed_urls:
                            save_discovered_seed(
                                url=seed_url,
                                domain=domain,
                                name=tc.get("title", domain),
                                source_type=tc.get("source_type", "Central Government"),
                                is_authoritative=tc.get("is_authoritative", False),
                                discovery_source=f"Web search: {topic[:60]}"
                            )
                            known_seed_urls.add(norm)
                            new_domains_found += 1

                    all_candidates.append({
                        "url": url,
                        "anchor_text": tc.get("title", ""),
                        "parent_seed": f"Web Search: {topic[:40]}...",
                        "depth": 1,
                        "is_external_discovery": True,
                        "source_type": tc.get("source_type", "Central Government"),
                        "is_authoritative": tc.get("is_authoritative", False),
                        "classification_reason": tc.get("classification_reason", "")
                    })

            if new_domains_found:
                print(f"  [FRONTIER EXPANSION] Discovered and saved {new_domains_found} brand-new portal domains to DB for future runs!")

        return all_candidates

    # ──────────────────────────────────────────────────────────────────────
    # BFS MULTI-HOP TRAVERSAL
    # ──────────────────────────────────────────────────────────────────────
    def _bfs_discover(
        self,
        seeds: List[Dict[str, Any]],
        max_links_per_seed: int = 8,
        depth: int = 2,
        max_pages_to_crawl: int = 8,
        save_new_domains: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Multi-hop BFS across seed URLs.

        For EACH page crawled:
          - Extracts all outbound hyperlinks matching scholarship keywords.
          - If a link points to a NEW external domain never seen before:
              → Adds it to the BFS frontier for crawling (depth permitting)
              → Saves it permanently to the DB as a future seed (Tier 2 expansion)
          - Returns all found candidate URLs for the pipeline to process.
        """
        from storage.database import save_discovered_seed, init_db
        init_db()

        known_seed_domains = {
            re.sub(r'^www\.', '', urlparse(s["url"]).netloc.lower())
            for s in SEED_SOURCES
        }

        # Prioritize HIGH priority seeds, DB discovered seeds, then others
        def seed_sort_key(s):
            if s.get("_from_db"):
                return 0
            p = s.get("priority", "MEDIUM")
            return 1 if p == "HIGH" else (2 if p == "MEDIUM" else 3)

        sorted_seeds = sorted(seeds, key=seed_sort_key)
        # Seed the frontier with the top priority portals
        frontier: List[Tuple[str, str, int]] = [
            (s["url"], s["name"], 1) for s in sorted_seeds[:max_pages_to_crawl]
        ]
        candidates: List[Dict[str, Any]] = []
        visited_urls: Set[str] = set()
        saved_domains_this_session: Set[str] = set()
        pages_crawled = 0

        while frontier and pages_crawled < max_pages_to_crawl:
            current_url, parent_label, current_depth = frontier.pop(0)
            if current_url in visited_urls:
                continue
            visited_urls.add(current_url)
            pages_crawled += 1

            status_code, html, final_url = self.fetcher.fetch(current_url)
            if status_code != 200 or not html:
                continue

            soup = BeautifulSoup(html, "html.parser")
            base_url = final_url or current_url
            current_domain = urlparse(base_url).netloc.lower()
            current_domain_root = re.sub(r'^www\.', '', current_domain)

            links_extracted_this_page = 0
            for tag in soup.find_all("a", href=True):
                href = tag.get("href", "").strip()
                if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
                    continue

                full_url = urljoin(base_url, href)
                parsed = urlparse(full_url)

                # Skip binary/media files
                if any(parsed.path.lower().endswith(ext) for ext in IGNORE_EXTENSIONS):
                    continue

                link_domain = parsed.netloc.lower()
                link_domain_root = re.sub(r'^www\.', '', link_domain)

                # Skip blocked domains
                if link_domain_root in BLOCKED_DOMAINS:
                    continue

                link_text = tag.get_text(separator=" ", strip=True).lower()
                url_lower = full_url.lower()
                has_keyword = any(k in link_text or k in url_lower for k in SCHOLARSHIP_KEYWORDS)

                if has_keyword and full_url not in self.discovered_urls:
                    self.discovered_urls.add(full_url)
                    source_type, is_auth, reason = SourceClassifier.classify_source(full_url)
                    is_external = link_domain != current_domain

                    candidates.append({
                        "url": full_url,
                        "anchor_text": tag.get_text(strip=True)[:100],
                        "parent_seed": parent_label,
                        "depth": current_depth,
                        "is_external_discovery": is_external,
                        "source_type": source_type,
                        "is_authoritative": is_auth,
                        "classification_reason": reason
                    })
                    links_extracted_this_page += 1

                    # ── TIER 3: Persistent Frontier Expansion ─────────────
                    cand_link_text = (link_text + " " + full_url).lower()
                    is_edu_link = any(k in cand_link_text for k in [
                        "scholarship", "fellowship", "stipend", "student", "education",
                        "post-matric", "pre-matric", "inspire", "pragati", "jrf", "phd", "chhatravritti"
                    ])

                    if (is_external
                            and is_auth
                            and source_type != "Non-Educational Government / Utility"
                            and is_edu_link
                            and link_domain_root not in known_seed_domains
                            and link_domain_root not in BLOCKED_DOMAINS
                            and link_domain_root not in saved_domains_this_session
                            and save_new_domains):

                        seed_base = f"{parsed.scheme}://{parsed.netloc}"
                        save_discovered_seed(
                            url=seed_base,
                            domain=link_domain,
                            name=tag.get_text(strip=True)[:80] or link_domain,
                            source_type=source_type,
                            is_authoritative=is_auth,
                            discovery_source=f"BFS from {parent_label[:60]}"
                        )
                        saved_domains_this_session.add(link_domain_root)
                        print(f"  [NEW DOMAIN DISCOVERED] '{link_domain}' found via '{parent_label[:40]}' -> saved as future seed")

                    # Queue for deeper traversal if within depth limit
                    if current_depth < depth and is_external and is_auth:
                        frontier.append((full_url, f"Discovered: {link_domain}", current_depth + 1))

                    if links_extracted_this_page >= max_links_per_seed:
                        break

        return candidates

    # ──────────────────────────────────────────────────────────────────────
    # LEGACY PUBLIC METHOD (kept for backward compatibility with pipeline.py)
    # ──────────────────────────────────────────────────────────────────────
    def discover_from_seeds(self, max_links_per_seed: int = 10, depth: int = 3) -> List[Dict[str, Any]]:
        """Backward-compatible wrapper — now delegates to _bfs_discover with all seeds."""
        return self._bfs_discover(
            seeds=SEED_SOURCES,
            max_links_per_seed=max_links_per_seed,
            depth=depth,
            save_new_domains=True
        )

    def load_source_documents(self) -> List[Dict[str, Any]]:
        """
        Loads crawled official portal documents from data/source_documents/
        for automated NLP extraction and verification.
        """
        from pathlib import Path
        doc_dir = Path(__file__).resolve().parent.parent / "data" / "source_documents"
        targets = []
        if not doc_dir.exists():
            return targets

        for doc_file in sorted(doc_dir.glob("*.txt")):
            doc_id = doc_file.stem
            content = doc_file.read_text(encoding="utf-8")

            url = ""
            app_url = ""
            provider = ""
            name = ""
            source_type = "Central Government"
            body = content

            if "---" in content:
                header_part, body = content.split("---", 1)
                for line in header_part.splitlines():
                    if line.startswith("OFFICIAL_SOURCE_URL:"):
                        url = line.split(":", 1)[1].strip()
                    elif line.startswith("APPLICATION_URL:"):
                        app_url = line.split(":", 1)[1].strip()
                    elif line.startswith("PROVIDER:"):
                        provider = line.split(":", 1)[1].strip()
                    elif line.startswith("SCHEME_NAME:"):
                        name = line.split(":", 1)[1].strip()
                    elif line.startswith("SOURCE_TYPE:"):
                        source_type = line.split(":", 1)[1].strip()

            targets.append({
                "id": doc_id,
                "url": url,
                "application_url": app_url,
                "provider": provider,
                "name": name,
                "source_type": source_type,
                "raw_content": body.strip()
            })

        return targets

    def discover_from_query(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Open-web DuckDuckGo search discovery.
        Finds scholarship portals not linked from any known source.
        """
        candidates: List[Dict[str, Any]] = []
        try:
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                try:
                    from ddgs import DDGS
                except ImportError:
                    from duckduckgo_search import DDGS


            search_query = query
            if not any(k in query.lower() for k in ["scholarship", "scheme", "fellowship", "grant", "portal"]):
                search_query = f"{query} scholarship scheme"

            with DDGS() as ddgs:
                try:
                    results = list(ddgs.text(search_query, backend="html", max_results=max_results))
                except Exception:
                    results = list(ddgs.text(search_query, backend="lite", max_results=max_results))

            for r in results:
                url = r.get("href") or r.get("link", "")
                if not url:
                    continue
                parsed = urlparse(url)
                domain_root = re.sub(r'^www\.', '', parsed.netloc.lower())
                if domain_root in BLOCKED_DOMAINS:
                    continue
                title = r.get("title", "")
                source_type, is_auth, reason = SourceClassifier.classify_source(url)
                candidates.append({
                    "url": url,
                    "title": title,
                    "snippet": r.get("body", ""),
                    "source_type": source_type,
                    "is_authoritative": is_auth,
                    "classification_reason": reason
                })
        except Exception as e:
            print(f"[DISCOVERY ERROR] Open-web query failed: {e}")

        return candidates

    def fetch_and_clean_page(self, url: str) -> Dict[str, Any]:
        """
        Fetches a live URL, strips boilerplate, and returns clean text + title.
        """
        status_code, html, final_url = self.fetcher.fetch(url)
        if status_code != 200 or not html:
            return {
                "success": False,
                "status_code": status_code,
                "url": url,
                "title": "",
                "clean_text": "",
                "error": f"HTTP status {status_code}"
            }

        soup = BeautifulSoup(html, "html.parser")

        title = ""
        if soup.title and soup.title.string:
            title = soup.title.string.strip()
        elif soup.find("h1"):
            title = soup.find("h1").get_text(strip=True)

        for element in soup(["script", "style", "nav", "footer", "header", "noscript", "svg"]):
            element.decompose()

        clean_text = soup.get_text(separator="\n", strip=True)

        return {
            "success": True,
            "status_code": status_code,
            "url": final_url or url,
            "title": title,
            "clean_text": clean_text
        }
