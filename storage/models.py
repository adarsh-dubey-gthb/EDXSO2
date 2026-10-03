"""
Data models and schemas for Scholarship Intelligence Crawler.
Conforms strictly to Edxso / Atlas Funding requirements.
"""

from dataclasses import dataclass, asdict, field
from typing import Optional, List, Dict, Any
from datetime import datetime

@dataclass
class ScholarshipRecord:
    # Core Identification
    id: str
    name: str
    provider: str
    
    # Official Source & Links
    official_source: str
    application_url: str
    source_type: str  # "Central Government", "State Government", "Corporate CSR", "University / Premier Institution", "Statutory Body / Ministry"
    
    # Financial & Academic Eligibility
    amount: str
    eligibility: str
    academic_requirements: str
    course_level: str
    income_criteria: str
    age_criteria: str
    gender_criteria: str
    category_criteria: str
    domicile_requirements: str
    institution_requirements: str
    
    # Timeline
    opening_date: str
    closing_date: str
    
    # Process & Operational Details
    documents_required: str
    selection_process: str
    renewal_requirements: str
    
    # Status & AI Verification Engine Outputs
    current_status: str  # ACTIVE, EXPIRING_SOON, EXPIRED, REVIEW_REQUIRED, NO_LONGER_VERIFIABLE
    confidence_score: float  # Percentage (e.g. 98.4%)
    verification_status: str  # "VERIFIED" (>=95%) or "REVIEW_REQUIRED" (<95%)
    date_last_verified: str
    why_this_score: str  # Detailed multi-factor explanation breakdown
    
    # Source Evidence
    source_evidence: str  # Primary supporting evidence snippet
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class VerificationEvidence:
    scholarship_id: str
    field_name: str
    evidence_quote: str
    source_url: str
    verified_at: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class ChangeLogEntry:
    scholarship_id: str
    field_name: str
    old_value: str
    new_value: str
    date_detected: str
    source: str
    evidence: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class CrawlRunSummary:
    run_id: int
    timestamp: str
    total_discovered: int
    verified_count: int
    review_required_count: int
    active_count: int
    expired_count: int
    changes_detected_count: int
    avg_confidence: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
