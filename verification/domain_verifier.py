"""
Domain and Authority Verification Engine.
Assesses whether a given URL belongs to an authoritative primary source.
"""

from typing import Dict, Any, Tuple
from crawler.classifier import SourceClassifier
from config.settings import KNOWN_AGGREGATORS

class DomainVerifier:
    @classmethod
    def verify_domain_authority(cls, url: str) -> Tuple[float, Dict[str, Any]]:
        """
        Evaluates domain authority.
        Returns: (score [0.0 - 1.0], audit_details)
        """
        source_type, is_auth, reason = SourceClassifier.classify_source(url)
        domain = SourceClassifier.extract_domain(url)
        
        # Check aggregators explicitly
        for agg in KNOWN_AGGREGATORS:
            if agg in domain:
                return 0.0, {
                    "domain": domain,
                    "source_type": "Aggregator",
                    "is_authoritative": False,
                    "score": 0.0,
                    "notes": f"Disqualified as authoritative source: matches aggregator pattern '{agg}'."
                }
                
        if source_type in ["Central Government", "State Government", "Statutory Body / Ministry"]:
            score = 1.0
        elif source_type == "University / Premier Institution":
            score = 1.0
        elif source_type == "Corporate CSR":
            score = 0.96  # High-trust verified official corporate foundation
        else:
            score = 0.25  # Generic unverified website
            
        return score, {
            "domain": domain,
            "source_type": source_type,
            "is_authoritative": is_auth,
            "score": score,
            "notes": reason
        }
