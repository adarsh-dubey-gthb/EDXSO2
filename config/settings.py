"""
System configuration and parameter settings for Scholarship Intelligence Crawler.
"""

from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "scholarships.db"

# Confidence & Verification Thresholds
VERIFIED_CONFIDENCE_THRESHOLD = 0.95  # Strict assignment requirement: >= 95% is VERIFIED
EXPIRING_SOON_DAYS = 14  # Mark EXPIRING_SOON if deadline within 14 days

# Factor Weights for Deterministic Confidence Calculation
# Total must equal 1.00
CONFIDENCE_WEIGHTS = {
    "domain_authenticity": 0.25,   # Primary official domain (.gov.in, .nic.in, .ac.in, whitelisted CSR)
    "source_liveness": 0.20,       # Official page HTTP 200 & title/scheme presence verified
    "evidence_grounding": 0.20,    # Key fields traceable to exact verbatim text quotes
    "application_url_auth": 0.15,  # Verified accessible official application link
    "temporal_validity": 0.10,     # Freshness, active deadlines vs stale/expired states
    "schema_completeness": 0.10    # Minimum mandatory fields non-empty and non-contradictory
}

# Recognized High-Trust Official Government / Academic TLDs
OFFICIAL_TLDS = [
    ".gov.in",
    ".nic.in",
    ".ac.in",
    ".edu.in",
    ".org.in",
    ".res.in"
]

# Whitelisted Official Corporate CSR & Foundation Domains
# (These represent the verified primary domains of corporate & philanthropic grant-makers)
OFFICIAL_CSR_DOMAINS = [
    "tatatrusts.org",
    "tatasteel.com",
    "reliancefoundation.org",
    "scholarships.reliancefoundation.org",
    "ongcscholar.org",
    "ongcindia.com",
    "infosys.org",
    "hdfcbank.com",
    "kotakeducation.org",
    "loreal.com",
    "kotak.com",
    "wipro.com",
    "azimpremjifoundation.org",
    "mahindrarise.com",
    "mahindra.com",
    "bajajfinserv.in",
    "hero.com",
    "herofinancorp.com",
    "bhartiairtel.com",
    "airtel.in",
    "adanigroup.com",
    "adanifoundation.org",
]

# Disallowed Aggregators - Allowed for initial discovery, strictly forbidden as primary authority
KNOWN_AGGREGATORS = [
    "buddy4study.com",
    "scholarshipsads.com",
    "shiksha.com",
    "collegedunia.com",
    "careers360.com",
    "jagranjosh.com",
    "sarkariresult.com",
    "embibe.com"
]

# Standard Status Enums
STATUS_ACTIVE = "ACTIVE"
STATUS_EXPIRING_SOON = "EXPIRING_SOON"
STATUS_EXPIRED = "EXPIRED"
STATUS_REVIEW_REQUIRED = "REVIEW_REQUIRED"
STATUS_NO_LONGER_VERIFIABLE = "NO_LONGER_VERIFIABLE"
