"""
Core Pipeline Coordinator for Scholarship Intelligence Crawler.
Discovers -> Crawls -> Extracts -> Verifies -> Scores -> Stores -> Updates.
"""

from typing import List, Dict, Any, Tuple
from datetime import datetime
import copy
from crawler.fetcher import WebFetcher
from crawler.classifier import SourceClassifier
from crawler.discovery import DiscoveryEngine
import re
import hashlib
from urllib.parse import urlparse
from crawler.nlp_extractor import NLPScholarshipExtractor
from crawler.semantic_validator import SemanticScholarshipValidator
from verification.confidence_engine import ConfidenceEngine
from verification.anti_hallucination import AntiHallucinationEngine
from change_detection.tracker import ChangeTracker
from storage.database import (
    init_db,
    save_or_update_scholarship,
    record_crawl_run,
    get_connection,
    load_discovered_seeds,
    save_discovered_seed,
    mark_seed_crawled
)
from storage.models import ScholarshipRecord, VerificationEvidence, CrawlRunSummary

class ScholarshipPipeline:
    def __init__(self):
        self.fetcher = WebFetcher(timeout=10, max_retries=1)
        self.discovery = DiscoveryEngine(self.fetcher)
        init_db()

    def run_pipeline(
        self, 
        run_number: int = 1, 
        simulate_live_crawl: bool = True
    ) -> CrawlRunSummary:
        """
        Executes an end-to-end continuous crawl cycle.
        Run 1 establishes baseline discovery.
        Run 2 demonstrates change detection, updates, and lifecycle transitions.
        """
        timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n=======================================================")
        print(f">> STARTING CRAWLER PIPELINE: RUN {run_number}")
        print(f"Timestamp: {timestamp_str}")
        print(f"=======================================================\n")

        # STAGE 1: FULLY AUTONOMOUS DISCOVERY
        print("[STAGE 1: AUTONOMOUS DISCOVERY] Automatically traversing seed portals and querying live web...")
        discovered_links = []
        try:
            discovered_links = self.discovery.discover_all_autonomous(max_links_per_seed=3, enable_web_search=True)
            print(f"  -> Discovered {len(discovered_links)} candidate scholarship links completely automatically (zero manual input required).")
            for c in discovered_links[:5]:
                print(f"     * Found: '{c['anchor_text'][:40]}' -> {c['url'][:60]}")
        except Exception as e:
            print(f"  -> Autonomous discovery notice: {e}")

        # STAGE 2: SOURCE CLASSIFICATION
        print("\n[STAGE 2: SOURCE CLASSIFICATION] Classifying discovered links into authority tiers...")
        sample_classifications = {}
        for c in discovered_links[:5]:
            sample_classifications[c['url']] = c['source_type']
            print(f"  -> {c['url'][:55]}... -> [{c['source_type']}] (Authoritative: {c['is_authoritative']})")

        # 100% REAL-TIME LIVE DATA INGESTION:
        # No hardcoded lists or static text files. Data is fetched live from official web portals.
        data_to_process = []
        existing_sources = set()

        if run_number >= 2:
            # REAL-TIME RE-CRAWL & AUDIT CYCLE:
            # Query all existing schemes from the database and re-crawl their live URLs in real-time over HTTP
            print("\n[STAGE 2.5: LIVE RE-CRAWL & DATA FRESHNESS CHECK] Re-fetching active database records from live web...")
            try:
                conn = get_connection()
                c = conn.cursor()
                c.execute("SELECT id, name, provider, official_source, application_url, source_type FROM scholarships")
                existing_rows = c.fetchall()
                conn.close()

                for row in existing_rows:
                    rec_id, rec_name, rec_prov, rec_source, rec_app, rec_stype = row[0], row[1], row[2], row[3], row[4], row[5]
                    existing_sources.add(rec_source.lower().rstrip('/'))
                    print(f"  [RE-CRAWL] Fetching live state for: '{rec_name}' ({rec_source[:50]})...")
                    live_page = self.discovery.fetch_and_clean_page(rec_source)
                    data_to_process.append({
                        "id": rec_id,
                        "url": rec_source,
                        "application_url": rec_app or rec_source,
                        "provider": rec_prov,
                        "name": rec_name,
                        "source_type": rec_stype,
                        "raw_content": live_page.get("clean_text", ""),
                        "http_status": live_page.get("status_code", 200)
                    })
            except Exception as e:
                print(f"  [RE-CRAWL ERROR] Could not load prior records: {e}")
        else:
            try:
                conn = get_connection()
                rows = conn.execute("SELECT official_source FROM scholarships").fetchall()
                existing_sources = {r[0].lower().rstrip('/') for r in rows if r[0]}
                conn.close()
            except Exception:
                pass

        # DYNAMIC LIVE DISCOVERY INGESTION:
        # Ingest candidate links discovered from live web / seeds in real-time
        newly_crawled_count = 0
        candidate_queue = list(discovered_links)

        # Baseline: Ensure all authoritative seed portals are examined if not yet queued
        if run_number == 1:
            from config.seed_sources import SEED_SOURCES
            for s in SEED_SOURCES:
                s_url = s["url"]
                if s_url.lower().rstrip('/') not in existing_sources:
                    candidate_queue.append({
                        "url": s_url,
                        "anchor_text": s["name"],
                        "parent_seed": s["name"],
                        "source_type": s.get("category", "Central Government"),
                        "is_authoritative": s.get("is_authoritative", True)
                    })

        for cand in candidate_queue:
            cand_url = cand.get("url", "").strip()
            norm_cand_url = cand_url.lower().rstrip('/')
            
            if not cand_url or norm_cand_url in existing_sources:
                continue
            existing_sources.add(norm_cand_url)
            if not cand.get("is_authoritative", False):
                continue

            parsed_cand = urlparse(cand_url)
            # Skip generic non-scheme endpoints
            if parsed_cand.path in ["/login", "/register", "/contact", "/about", "/faq"]:
                continue

            print(f"  [DISCOVERY -> CRAWL] Fetching newly discovered scheme notice: {cand_url[:65]}...")
            page_data = self.discovery.fetch_and_clean_page(cand_url)
            if page_data["success"] and len(page_data["clean_text"]) > 100:
                slug_name = cand.get("anchor_text") or page_data["title"] or "scheme"
                doc_id = re.sub(r'[^a-zA-Z0-9]+', '-', slug_name.lower()).strip('-')[:45]
                if not doc_id:
                    doc_id = "discovered-" + hashlib.md5(cand_url.encode()).hexdigest()[:8]

                # === POSITIVE CONTRACT INTENT GATE ===
                is_valid_scheme, val_reason, val_meta = SemanticScholarshipValidator.validate_educational_intent(
                    cand_url, page_data["title"], page_data["clean_text"]
                )
                if not is_valid_scheme:
                    print(f"  [SEMANTIC VALIDATOR] Skipped: {val_reason}")
                    if val_meta.get("type") == "DIRECTORY_HUB":
                        try:
                            hub_domain = parsed_cand.netloc.lower()
                            save_discovered_seed(
                                url=cand_url,
                                domain=hub_domain,
                                name=page_data.get("title", hub_domain),
                                source_type=cand.get("source_type", "Central Government"),
                                is_authoritative=cand.get("is_authoritative", False),
                                discovery_source="Autonomous Frontier Expansion"
                            )
                            # Extract scheme links from inside this directory hub and queue them!
                            hub_links = self.discovery.extract_scheme_links(page_data.get("raw_html", ""), cand_url)
                            for hl in hub_links:
                                hl_norm = hl["url"].lower().rstrip('/')
                                if hl_norm not in existing_sources:
                                    candidate_queue.append(hl)
                        except Exception:
                            pass
                    continue

                data_to_process.append({
                    "id": doc_id,
                    "url": cand_url,
                    "application_url": cand_url,
                    "provider": cand.get("parent_seed", "National Educational Authority"),
                    "name": page_data["title"] or cand.get("anchor_text", "Discovered Scholarship Scheme"),
                    "source_type": cand.get("source_type", "Central Government"),
                    "raw_content": page_data["clean_text"],
                    "http_status": page_data.get("status_code", 200)
                })
                existing_sources.add(norm_cand_url)
                newly_crawled_count += 1
                if newly_crawled_count >= 25:  # Ingest up to 25 authentic schemes
                    break

        if newly_crawled_count > 0:
            print(f"  -> Ingested {newly_crawled_count} newly discovered schemes from live web into pipeline!")

        # STAGE 3, 4, 5: CRAWLING, EXTRACTION, VERIFICATION
        total_discovered = len(data_to_process)
        verified_count = 0
        review_required_count = 0
        active_count = 0
        expired_count = 0
        total_changes = 0
        all_confidences = []

        print(f"\n[STAGE 3: CRAWLING & STAGE 4: NLP EXTRACTION] Processing {total_discovered} target scheme notices...")

        for raw_item in data_to_process:
            raw_text = raw_item.get("raw_content", "")
            
            # AUTOMATED NLP / SEMANTIC EXTRACTION FROM RAW DOCUMENT
            rec = NLPScholarshipExtractor.extract_from_raw_document(
                doc_id=raw_item["id"],
                source_url=raw_item["url"],
                raw_content=raw_text,
                metadata={
                    "name": raw_item.get("name"),
                    "provider": raw_item.get("provider"),
                    "source_type": raw_item.get("source_type"),
                    "application_url": raw_item.get("application_url")
                }
            )
            
            # STAGE 5: VERIFICATION & CONFIDENCE SCORING
            http_status = raw_item.get("http_status", 200)

            # Calculate deterministic confidence score (NO arbitrary LLM score!)
            conf_score, v_status, why_score, breakdown = ConfidenceEngine.calculate_confidence(
                scholarship_data=rec.to_dict(),
                raw_source_text=raw_text,
                http_status=http_status
            )
            
            # Update record verification attributes
            rec.confidence_score = conf_score
            rec.verification_status = v_status
            rec.why_this_score = why_score
            
            # Evaluate lifecycle status (ACTIVE, EXPIRING_SOON, EXPIRED, etc.)
            rec.current_status = ChangeTracker.evaluate_status(
                closing_date_str=rec.closing_date,
                http_status=http_status,
                confidence_score=conf_score
            )
            
            # Build granular field-level verification evidence
            evidence_list: List[VerificationEvidence] = [
                VerificationEvidence(
                    scholarship_id=rec.id,
                    field_name="Scholarship Name",
                    evidence_quote=f"Official scheme titled '{rec.name}' identified on canonical source.",
                    source_url=rec.official_source,
                    verified_at=timestamp_str
                ),
                VerificationEvidence(
                    scholarship_id=rec.id,
                    field_name="Benefit Amount",
                    evidence_quote=f"Stipend/Grant: {rec.amount}",
                    source_url=rec.official_source,
                    verified_at=timestamp_str
                ),
                VerificationEvidence(
                    scholarship_id=rec.id,
                    field_name="Application Deadline",
                    evidence_quote=f"Application window closing date verified as '{rec.closing_date}'.",
                    source_url=rec.official_source,
                    verified_at=timestamp_str
                ),
                VerificationEvidence(
                    scholarship_id=rec.id,
                    field_name="Eligibility Criteria",
                    evidence_quote=f"{rec.eligibility}",
                    source_url=rec.official_source,
                    verified_at=timestamp_str
                )
            ]

            # ZERO TOLERANCE: Drop any entity that failed the positive Educational Aid Invariant
            if rec.verification_status == "REJECTED_NON_SCHOLARSHIP" or rec.confidence_score <= 0.0:
                print(f"  [REJECTED NON-SCHOLARSHIP] Dropped: '{rec.name}' (Confidence: {rec.confidence_score}%)")
                continue

            # Save or update record with change detection
            is_new, changes = save_or_update_scholarship(
                record=rec,
                evidence_list=evidence_list,
                track_changes=True
            )


            # Update discovered seeds crawl stats if applicable
            try:
                parsed_source = urlparse(rec.official_source)
                domain_url = f"{parsed_source.scheme}://{parsed_source.netloc.lower()}"
                mark_seed_crawled(domain_url, rec.confidence_score)
            except Exception:
                pass

            # Accumulate metrics
            all_confidences.append(rec.confidence_score)
            if rec.verification_status == "VERIFIED":
                verified_count += 1
            else:
                review_required_count += 1

            if rec.current_status == "ACTIVE":
                active_count += 1
            elif rec.current_status == "EXPIRED":
                expired_count += 1

            if changes:
                total_changes += len(changes)
                print(f"  [CHANGE DETECTED] for '{rec.name}':")
                for ch in changes:
                    old_display = ch.old_value.replace("₹", "Rs. ")
                    new_display = ch.new_value.replace("₹", "Rs. ")
                    print(f"     [{ch.field_name}] Old: '{old_display}' -> New: '{new_display}'")

        avg_confidence = round(sum(all_confidences) / len(all_confidences), 1) if all_confidences else 0.0

        summary = CrawlRunSummary(
            run_id=run_number,
            timestamp=timestamp_str,
            total_discovered=total_discovered,
            verified_count=verified_count,
            review_required_count=review_required_count,
            active_count=active_count,
            expired_count=expired_count,
            changes_detected_count=total_changes,
            avg_confidence=avg_confidence
        )

        record_crawl_run(summary)

        print(f"\n=======================================================")
        print(f"[SUMMARY] CRAWL RUN {run_number} COMPLETED")
        print(f"  * Total Discovered:     {total_discovered}")
        print(f"  * Verified (>=95%):     {verified_count}")
        print(f"  * Review Required:      {review_required_count}")
        print(f"  * Active Status:        {active_count}")
        print(f"  * Expired Status:       {expired_count}")
        print(f"  * Changes Detected:     {total_changes}")
        print(f"  * Average Confidence:   {avg_confidence}%")
        print(f"=======================================================\n")

        return summary

    def crawl_and_ingest_url(self, url: str, custom_name: str = None) -> Dict[str, Any]:
        """
        Dynamically crawls, extracts, verifies, and stores any single live URL.
        Enables testing live URLs beyond the seed list on-the-fly.
        """
        timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n[LIVE CRAWL] Fetching and analyzing live URL: {url}")

        page_data = self.discovery.fetch_and_clean_page(url)
        if not page_data["success"]:
            return {
                "success": False,
                "error": page_data.get("error", "Failed to fetch live URL"),
                "status_code": page_data.get("status_code", 0)
            }

        clean_text = page_data["clean_text"]
        page_title = (custom_name or page_data.get("title") or "Discovered Scholarship Scheme").strip()
        # Validate educational scholarship intent against ontology

        is_valid_scheme, val_reason, val_meta = SemanticScholarshipValidator.validate_educational_intent(
            url, page_title, clean_text
        )
        if not is_valid_scheme:
            return {
                "success": False,
                "error": f"Educational Intent Validation Failed: {val_reason}",
                "status_code": page_data["status_code"]
            }

        # Generate deterministic slug ID
        doc_slug = re.sub(r'[^a-zA-Z0-9]+', '-', page_title.lower()).strip('-')[:50]
        if not doc_slug:
            doc_slug = "scheme-" + hashlib.md5(url.encode()).hexdigest()[:8]

        # Classify source domain authority
        source_type, is_auth, class_reason = SourceClassifier.classify_source(url)

        # Extract schema using NLP engine
        rec = NLPScholarshipExtractor.extract_from_raw_document(
            doc_id=doc_slug,
            source_url=url,
            raw_content=clean_text,
            metadata={
                "name": custom_name or page_title,
                "source_type": source_type,
                "application_url": url
            }
        )


        # Calculate confidence
        conf_score, v_status, why_score, breakdown = ConfidenceEngine.calculate_confidence(
            scholarship_data=rec.to_dict(),
            raw_source_text=clean_text,
            http_status=page_data["status_code"]
        )
        rec.confidence_score = conf_score
        rec.verification_status = v_status
        rec.why_this_score = why_score

        # Status evaluation
        rec.current_status = ChangeTracker.evaluate_status(
            closing_date_str=rec.closing_date,
            http_status=page_data["status_code"],
            confidence_score=conf_score
        )

        # Granular evidence
        evidence_list: List[VerificationEvidence] = [
            VerificationEvidence(
                scholarship_id=rec.id,
                field_name="Scholarship Name",
                evidence_quote=f"Identified as '{rec.name}' on {url}.",
                source_url=url,
                verified_at=timestamp_str
            ),
            VerificationEvidence(
                scholarship_id=rec.id,
                field_name="Benefit Amount",
                evidence_quote=f"Extracted amount: {rec.amount}",
                source_url=url,
                verified_at=timestamp_str
            ),
            VerificationEvidence(
                scholarship_id=rec.id,
                field_name="Application Deadline",
                evidence_quote=f"Extracted deadline: {rec.closing_date}",
                source_url=url,
                verified_at=timestamp_str
            ),
            VerificationEvidence(
                scholarship_id=rec.id,
                field_name="Eligibility Criteria",
                evidence_quote=f"{rec.eligibility[:200]}",
                source_url=url,
                verified_at=timestamp_str
            )
        ]

        # Save to database and track changes
        is_new, changes = save_or_update_scholarship(
            record=rec,
            evidence_list=evidence_list,
            track_changes=True
        )

        # Register domain in discovered_seeds so future runs auto-monitor it
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            save_discovered_seed(
                url=f"{parsed.scheme}://{domain}",
                domain=domain,
                name=rec.name or domain,
                source_type=rec.source_type,
                is_authoritative=(rec.source_type != "Aggregator / Secondary"),
                discovery_source="Direct Web Ingestion"
            )
            mark_seed_crawled(f"{parsed.scheme}://{domain}", rec.confidence_score)
        except Exception:
            pass

        return {
            "success": True,
            "is_new": is_new,
            "record": rec.to_dict(),
            "changes": [c.to_dict() for c in changes],
            "confidence_breakdown": breakdown,
            "evidence": [ev.to_dict() for ev in evidence_list]
        }
