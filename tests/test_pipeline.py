"""
Unit and Integration Test Suite for Scholarship Intelligence Crawler.
Validates classification, confidence formulation, anti-hallucination, change detection, and storage.
"""

import unittest
from datetime import datetime, timedelta
from crawler.classifier import SourceClassifier
from verification.domain_verifier import DomainVerifier
from verification.anti_hallucination import AntiHallucinationEngine
from verification.confidence_engine import ConfidenceEngine
from change_detection.tracker import ChangeTracker
from storage.database import init_db, save_or_update_scholarship, get_scholarship
from storage.models import ScholarshipRecord

class TestScholarshipPipeline(unittest.TestCase):
    def setUp(self):
        init_db()

    def test_source_classification(self):
        # Government domain
        cat, is_auth, _ = SourceClassifier.classify_source("https://scholarships.gov.in/scheme")
        self.assertEqual(cat, "Central Government")
        self.assertTrue(is_auth)

        # University domain
        cat, is_auth, _ = SourceClassifier.classify_source("https://www.iisc.ac.in/fellowships")
        self.assertEqual(cat, "University / Premier Institution")
        self.assertTrue(is_auth)

        # Official Corporate CSR
        cat, is_auth, _ = SourceClassifier.classify_source("https://scholarships.reliancefoundation.org")
        self.assertEqual(cat, "Corporate CSR")
        self.assertTrue(is_auth)

        # Aggregator domain (Forbidden as authoritative)
        cat, is_auth, _ = SourceClassifier.classify_source("https://www.buddy4study.com/scholarship")
        self.assertEqual(cat, "Aggregator / Secondary")
        self.assertFalse(is_auth)

    def test_anti_hallucination_sanitization(self):
        # Missing values must strictly be 'Not specified'
        self.assertEqual(AntiHallucinationEngine.sanitize_field(None), "Not specified")
        self.assertEqual(AntiHallucinationEngine.sanitize_field(""), "Not specified")
        self.assertEqual(AntiHallucinationEngine.sanitize_field("N/A"), "Not specified")
        self.assertEqual(AntiHallucinationEngine.sanitize_field("₹50,000"), "₹50,000")

    def test_anti_hallucination_grounding(self):
        source_text = "The AICTE Pragati scheme awards Rs. 50,000 per annum to meritorious girl students."
        
        # Grounded value
        is_grounded, quote = AntiHallucinationEngine.verify_grounding("Rs. 50,000", source_text)
        self.assertTrue(is_grounded)
        self.assertIsNotNone(quote)

        # Hallucinated value not present in text
        is_grounded, quote = AntiHallucinationEngine.verify_grounding("Rs. 10 Lakhs", source_text)
        self.assertFalse(is_grounded)

        # 'Not specified' should be non-hallucinatory
        is_grounded, quote = AntiHallucinationEngine.verify_grounding("Not specified", source_text)
        self.assertTrue(is_grounded)

    def test_deterministic_confidence_scoring(self):
        # 1. Authoritative Gov Source -> Confidence >= 95%
        rec_gov = {
            "name": "Central Sector Scheme of Scholarship for College and University Students",
            "provider": "Ministry of Education",
            "official_source": "https://scholarships.gov.in/schemes/css",
            "application_url": "https://scholarships.gov.in/schemes/css",
            "amount": "Rs. 12,000 per annum",
            "eligibility": "Class 12 top 20th percentile undergraduate students",
            "closing_date": "31 October 2026",
            "income_criteria": "Rs. 4.5 Lakh",
            "course_level": "Undergraduate",
            "selection_process": "Merit list",
            "documents_required": "Mark sheet"
        }
        raw_text = (
            "Ministry of Education notification for Central Sector Scheme of Scholarship for College and University Students. "
            "Financial benefit amount: Rs. 12,000 per annum for undergraduate degree course fees and maintenance stipend. "
            "Eligibility: Class 12 top 20th percentile college students. "
            "Income limit Rs. 4.5 Lakh. Application deadline: 31 October 2026."
        )
        conf, status, _, _ = ConfidenceEngine.calculate_confidence(rec_gov, raw_text, 200)
        self.assertGreaterEqual(conf, 95.0)
        self.assertEqual(status, "VERIFIED")

        # 2. Aggregator Source -> Disqualified from VERIFIED (Confidence < 95%)
        rec_agg = dict(rec_gov)
        rec_agg["official_source"] = "https://www.buddy4study.com/scholarship-details"
        conf_agg, status_agg, _, _ = ConfidenceEngine.calculate_confidence(rec_agg, raw_text, 200)
        self.assertLess(conf_agg, 95.0)
        self.assertEqual(status_agg, "REVIEW_REQUIRED")

    def test_change_detection_and_status(self):
        # Test status transitions
        ref_today = datetime(2026, 8, 1)
        
        # Active (deadline in future)
        status_future = ChangeTracker.evaluate_status("31 December 2026", 200, 98.0, reference_date=ref_today)
        self.assertEqual(status_future, "ACTIVE")

        # Expired (deadline passed)
        status_past = ChangeTracker.evaluate_status("31 December 2023", 200, 98.0, reference_date=ref_today)
        self.assertEqual(status_past, "EXPIRED")

        # Change Detection diff
        old_data = {"id": "test-1", "closing_date": "31 August 2026", "official_source": "https://example.gov.in"}
        new_data = {"id": "test-1", "closing_date": "15 September 2026", "official_source": "https://example.gov.in"}
        changes = ChangeTracker.diff_scholarships(old_data, new_data)
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0].field_name, "Deadline")
        self.assertEqual(changes[0].old_value, "31 August 2026")
        self.assertEqual(changes[0].new_value, "15 September 2026")

    def test_semantic_validator_positive_contract(self):
        from crawler.semantic_validator import SemanticScholarshipValidator
        
        # 1. Authentic educational scholarship -> Must PASS
        is_val, reason, _ = SemanticScholarshipValidator.validate_educational_intent(
            "https://aicte-india.org/schemes/pragati",
            "AICTE - Pragati Scholarship Scheme for Girl Students (Degree)",
            "Pragati scholarship scheme for girl students admitted to 1st year degree undergraduate course. Amount Rs 50,000 per annum towards tuition fee."
        )
        self.assertTrue(is_val)

        # 2. Non-educational civic service -> Must FAIL
        is_civic, reason_civic, _ = SemanticScholarshipValidator.validate_educational_intent(
            "https://serviceonline.bihar.gov.in/services/factory-license",
            "कारखाना लाइसेंस नवीकरण आवेदन",
            "कारखाना अधिनियम 1948 के तहत सभी फैक्ट्रियों के लिए वार्षिक लाइसेंस नवीकरण शुल्क।"
        )
        self.assertFalse(is_civic)

        # 3. Directory hub / portal gateway -> Must be REJECTED as scheme (routed to discovery seeds)
        is_hub, reason_hub, meta = SemanticScholarshipValidator.validate_educational_intent(
            "https://scholarships.gov.in/Students",
            "Students",
            "National Scholarship Portal student corner login schemes"
        )
        self.assertFalse(is_hub)
        self.assertEqual(meta.get("type"), "DIRECTORY_HUB")

    def test_dynamic_live_url_ingestion(self):
        from crawler.pipeline import ScholarshipPipeline
        from storage.database import get_connection
        pipeline = ScholarshipPipeline()
        
        # Test authentic scholarship ingestion
        res = pipeline.crawl_and_ingest_url(
            "https://scholarships.gov.in", 
            custom_name="Central Sector Scholarship Scheme for College Students"
        )
        self.assertTrue(res["success"])

        self.assertIn("record", res)
        self.assertEqual(res["record"]["source_type"], "Central Government")
        self.assertGreaterEqual(res["record"]["confidence_score"], 90.0)

        # Clean up test artifact from production database so it doesn't appear in dashboard
        conn = get_connection()
        conn.execute("DELETE FROM scholarships WHERE id LIKE '%central-sector-scholarship%'")
        conn.execute("DELETE FROM verification_evidence WHERE scholarship_id LIKE '%central-sector-scholarship%'")
        conn.commit()
        conn.close()

if __name__ == "__main__":
    unittest.main()

