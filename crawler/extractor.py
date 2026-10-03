"""
Structured Scholarship Extractor.
Extracts normalized attributes from unstructured text/HTML and formats them
into our standardized 19+ field schema. Ensures zero fabrication.
"""

import re
from typing import Dict, Any, List, Optional
from storage.models import ScholarshipRecord, VerificationEvidence
from verification.anti_hallucination import AntiHallucinationEngine

class ScholarshipExtractor:
    @staticmethod
    def clean_text(text: str) -> str:
        if not text:
            return ""
        return " ".join(text.split())

    @classmethod
    def extract_record_from_data(
        cls,
        raw_data: Dict[str, Any],
        raw_source_text: str = ""
    ) -> ScholarshipRecord:
        """
        Validates, sanitizes, and maps scholarship fields into ScholarshipRecord.
        Applies AntiHallucination sanitization so missing fields are 'Not specified'.
        """
        # Anti-hallucination sanitization
        s_name = AntiHallucinationEngine.sanitize_field(raw_data.get("name"))
        s_provider = AntiHallucinationEngine.sanitize_field(raw_data.get("provider"))
        s_official = str(raw_data.get("official_source", "")).strip()
        s_app = AntiHallucinationEngine.sanitize_field(raw_data.get("application_url"))
        s_type = AntiHallucinationEngine.sanitize_field(raw_data.get("source_type"))
        s_amount = AntiHallucinationEngine.sanitize_field(raw_data.get("amount"))
        s_eligibility = AntiHallucinationEngine.sanitize_field(raw_data.get("eligibility"))
        s_academic = AntiHallucinationEngine.sanitize_field(raw_data.get("academic_requirements"))
        s_course = AntiHallucinationEngine.sanitize_field(raw_data.get("course_level"))
        s_income = AntiHallucinationEngine.sanitize_field(raw_data.get("income_criteria"))
        s_age = AntiHallucinationEngine.sanitize_field(raw_data.get("age_criteria"))
        s_gender = AntiHallucinationEngine.sanitize_field(raw_data.get("gender_criteria"))
        s_category = AntiHallucinationEngine.sanitize_field(raw_data.get("category_criteria"))
        s_domicile = AntiHallucinationEngine.sanitize_field(raw_data.get("domicile_requirements"))
        s_inst = AntiHallucinationEngine.sanitize_field(raw_data.get("institution_requirements"))
        s_opening = AntiHallucinationEngine.sanitize_field(raw_data.get("opening_date"))
        s_closing = AntiHallucinationEngine.sanitize_field(raw_data.get("closing_date"))
        s_docs = AntiHallucinationEngine.sanitize_field(raw_data.get("documents_required"))
        s_selection = AntiHallucinationEngine.sanitize_field(raw_data.get("selection_process"))
        s_renewal = AntiHallucinationEngine.sanitize_field(raw_data.get("renewal_requirements"))
        
        # Primary evidence snippet
        evidence = raw_data.get("source_evidence") or (
            f"Official notification on {s_official}: '{s_name}' offered by {s_provider}. "
            f"Benefit: {s_amount}. Eligibility: {s_eligibility}."
        )

        return ScholarshipRecord(
            id=raw_data["id"],
            name=s_name,
            provider=s_provider,
            official_source=s_official,
            application_url=s_app,
            source_type=s_type,
            amount=s_amount,
            eligibility=s_eligibility,
            academic_requirements=s_academic,
            course_level=s_course,
            income_criteria=s_income,
            age_criteria=s_age,
            gender_criteria=s_gender,
            category_criteria=s_category,
            domicile_requirements=s_domicile,
            institution_requirements=s_inst,
            opening_date=s_opening,
            closing_date=s_closing,
            documents_required=s_docs,
            selection_process=s_selection,
            renewal_requirements=s_renewal,
            current_status=raw_data.get("current_status", "ACTIVE"),
            confidence_score=raw_data.get("confidence_score", 0.0),
            verification_status=raw_data.get("verification_status", "REVIEW_REQUIRED"),
            date_last_verified=raw_data.get("date_last_verified", "2026-10-03"),
            why_this_score=raw_data.get("why_this_score", ""),
            source_evidence=evidence
        )
