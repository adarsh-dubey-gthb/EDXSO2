"""
Change and Stale Data Tracking Engine.
Detects modifications between crawl runs, updates status based on deadlines,
and ensures complete audit logging of changes without loss of historical data.
"""

from datetime import datetime, date
import re
from typing import Optional, Tuple, Dict, Any, List
from config.settings import (
    STATUS_ACTIVE,
    STATUS_EXPIRING_SOON,
    STATUS_EXPIRED,
    STATUS_REVIEW_REQUIRED,
    STATUS_NO_LONGER_VERIFIABLE,
    EXPIRING_SOON_DAYS
)
from storage.models import ChangeLogEntry

class ChangeTracker:
    @staticmethod
    def parse_deadline(date_str: str) -> Optional[datetime]:
        """Attempts to parse varied human-readable deadline strings."""
        if not date_str or date_str == "Not specified":
            return None
            
        clean_str = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', date_str.strip())
        formats = [
            "%d %B %Y",      # 31 August 2026
            "%d %b %Y",       # 31 Aug 2026
            "%B %d, %Y",      # August 31, 2026
            "%Y-%m-%d",       # 2026-08-31
            "%d-%m-%Y",       # 31-08-2026
            "%d/%m/%Y",       # 31/08/2026
            "%B %Y"           # October 2026
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(clean_str, fmt)
            except ValueError:
                continue
        return None

    @classmethod
    def evaluate_status(
        cls, 
        closing_date_str: str, 
        http_status: int, 
        confidence_score: float,
        reference_date: Optional[datetime] = None
    ) -> str:
        """
        Determines current scholarship status based on live verification and dates.
        Statuses: ACTIVE, EXPIRING_SOON, EXPIRED, REVIEW_REQUIRED, NO_LONGER_VERIFIABLE
        """
        if http_status in [404, 410]:
            return STATUS_NO_LONGER_VERIFIABLE
            
        if confidence_score < 95.0:
            return STATUS_REVIEW_REQUIRED
            
        if not closing_date_str or closing_date_str == "Not specified":
            return STATUS_ACTIVE  # Rolling / ongoing scheme
            
        deadline = cls.parse_deadline(closing_date_str)
        if not deadline:
            return STATUS_ACTIVE
            
        today = reference_date if reference_date else datetime.now()
        
        if deadline < today:
            return STATUS_EXPIRED
            
        delta_days = (deadline - today).days
        if delta_days <= EXPIRING_SOON_DAYS:
            return STATUS_EXPIRING_SOON
            
        return STATUS_ACTIVE

    @classmethod
    def diff_scholarships(
        cls, 
        old_record: Dict[str, Any], 
        new_record: Dict[str, Any],
        detection_timestamp: Optional[str] = None
    ) -> List[ChangeLogEntry]:
        """
        Compares old scholarship record with newly fetched data.
        Returns a list of detected changes.
        """
        timestamp = detection_timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        changes: List[ChangeLogEntry] = []
        
        fields_to_track = [
            ("closing_date", "Deadline"),
            ("amount", "Benefit Amount"),
            ("eligibility", "Eligibility Criteria"),
            ("current_status", "Status"),
            ("application_url", "Application URL"),
            ("income_criteria", "Income Limit")
        ]
        
        for field_key, field_label in fields_to_track:
            old_val = str(old_record.get(field_key, "") or "").strip()
            new_val = str(new_record.get(field_key, "") or "").strip()
            
            if old_val and new_val and old_val != new_val:
                evidence = (
                    f"CHANGE DETECTED on {field_label}: "
                    f"Previous value '{old_val}' changed to '{new_val}' "
                    f"on official source {new_record.get('official_source')}."
                )
                entry = ChangeLogEntry(
                    scholarship_id=old_record.get("id"),
                    field_name=field_label,
                    old_value=old_val,
                    new_value=new_val,
                    date_detected=timestamp,
                    source=new_record.get("official_source", ""),
                    evidence=evidence
                )
                changes.append(entry)
                
        return changes
