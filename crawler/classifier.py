"""
Source and Domain Classifier.
Distinguishes between official sources (Government, Statutory, University, Corporate CSR)
and secondary aggregators/blogs.
"""

from urllib.parse import urlparse
from typing import Tuple, Dict, Any
from config.settings import OFFICIAL_TLDS, OFFICIAL_CSR_DOMAINS, KNOWN_AGGREGATORS

class SourceClassifier:
    @staticmethod
    def extract_domain(url: str) -> str:
        """Extracts the base domain hostname from a URL."""
        if not url:
            return ""
        parsed = urlparse(url)
        netloc = parsed.netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return netloc

    @classmethod
    def classify_source(cls, url: str) -> Tuple[str, bool, str]:
        """
        Classifies the source URL into an authoritative category.
        Returns: (source_type, is_authoritative, classification_reason)
        """
        if not url:
            return "Unknown", False, "No URL provided"
            
        domain = cls.extract_domain(url)
        
        # 1. Check if known aggregator
        for agg in KNOWN_AGGREGATORS:
            if agg in domain:
                return (
                    "Aggregator / Secondary",
                    False,
                    f"Third-party aggregator domain '{domain}'. Allowed for discovery only; prohibited as authoritative source."
                )
                
        # 2. Check Central & State Government (.gov.in, .nic.in)
        if domain.endswith(".gov.in") or domain.endswith(".nic.in"):
            # Exclude non-educational government departments (tourism, transport, land revenue, police, licenses)
            NON_EDUCATIONAL_GOV = [
                "tourism", "transport", "parivahan", "revenue", "bhumi", "land",
                "police", "excise", "forest", "irrigation", "pwd", "election",
                "court", "serviceonline", "labour", "migrant", "factory", "tender",
                "eproc", "procurement", "commercialtax", "vat", "property"
            ]
            if any(neg in domain for neg in NON_EDUCATIONAL_GOV):
                return (
                    "Non-Educational Government / Utility",
                    False,
                    f"Non-educational municipal/department portal ({domain}). Excluded from scholarship ingestion."
                )

            # State government portals usually have state name in domain (e.g. maharashtra.gov.in, up.gov.in)
            state_indicators = [
                "maharashtra", "up.gov", "kerala", "karnataka", "tamilnadu", "punjab", 
                "rajasthan", "gujarat", "bihar", "wb.gov", "oasis.gov.in", "mahadbt"
            ]
            if any(s in domain for s in state_indicators):
                return (
                    "State Government",
                    True,
                    f"Official State Government Portal domain ({domain})"
                )
            return (
                "Central Government",
                True,
                f"Official Government of India portal domain ({domain})"
            )
            
        # 3. Check Academic & University domains (.ac.in, .edu.in)
        if domain.endswith(".ac.in") or domain.endswith(".edu.in") or "pmrf.in" in domain:
            return (
                "University / Premier Institution",
                True,
                f"Accredited Higher Educational / Premier Research Institution domain ({domain})"
            )
            
        # 4. Check Statutory Bodies (e.g. AICTE, UGC)
        if any(stat in domain for stat in ["aicte-india.org", "ugc.ac.in", "ugcnet.nta.ac.in"]):
            return (
                "Statutory Body / Ministry",
                True,
                f"Official Indian statutory educational council domain ({domain})"
            )
            
        # 5. Check Official Corporate CSR & Philanthropic Foundations
        for csr_domain in OFFICIAL_CSR_DOMAINS:
            if csr_domain in domain:
                return (
                    "Corporate CSR",
                    True,
                    f"Verified Official Corporate CSR / Philanthropic Foundation domain ({domain})"
                )
                
        # 6. Fallback: Unverified non-authoritative domain
        return (
            "Other / Unverified",
            False,
            f"Domain '{domain}' is not recognized in the official registry of trusted educational authorities."
        )
