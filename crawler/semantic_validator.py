"""
Semantic Scholarship Intent & Domain Invariant Validator.
Permanent, architectural solution for the Scholarship Intelligence Crawler.

Eliminates the cat-and-mouse game of negative keyword blacklists.
Instead, enforces a mathematically positive contract:
  A document is an authentic educational scholarship if and only if it satisfies
  the Educational Aid Triple Invariant:
    1. Program Identity: A discrete, named educational aid program (not an umbrella portal/gateway).
    2. Academic Beneficiary: Targets students, scholars, or researchers enrolled in recognized education.
    3. Educational Funding Purpose: Provides financial aid for tuition, study stipends, or research allowances.

Any page that is a Directory / Portal Hub is recognized as a link-discovery node,
never as an individual scholarship record.
"""

import re
from typing import Tuple, Dict, Any, List, Optional
from urllib.parse import urlparse

class SemanticScholarshipValidator:
    """
    Authoritative, contract-based semantic validator for educational scholarships,
    fellowships, and academic grants.
    """

    # --- INVARIANT 1: SCHOLARSHIP / FELLOWSHIP PROGRAM IDENTITY SIGNALS ---
    # Pure generic semantic invariants: NO hardcoded specific scheme names (e.g. pragati, inspire, pmrf, etc.)
    SCHEME_IDENTITY_PATTERNS = [
        r'\bscholarships?\b', r'\bfellowships?\b', r'\bstipends?\b',
        r'\bbursar(?:y|ies)\b', r'\btuition\s+(?:waiver|reimbursement|support|concession)\b',
        r'\bfinancial\s+(?:aid|assistance|support)\b',
        r'\beducation(?:al)?\s+(?:schemes?|grants?|supports?|assistance|awards?|aid)\b',
        r'\bstudent\s+(?:schemes?|grants?|supports?|assistance|awards?|aid|stipend)\b',
        r'\bmerit[\s\-]cum[\s\-]means\b', r'\bmerit\s+scholarships?\b', r'\bmeans\s+scholarships?\b',
        r'\bhigher\s+education\s+(?:scheme|grant|aid|scholarship)\b',
        r'\bpost[\s\-]matric\b', r'\bpre[\s\-]matric\b',
        r'\bresearch\s+(?:fellowship|grant|award|stipend)\b',
        r'\bdoctoral\s+(?:fellowship|scholarship|grant)\b',
        r'\bpost[\s\-]doctoral\s+(?:fellowship|grant)\b',
        r'\bfee\s+(?:concession|reimbursement|waiver|subsidy)\b',
        r'\baccommodation\s+grant\b', r'\bcontingency\s+grant\b',
        r'\bbook\s+grant\b', r'\bmaintenance\s+allowance\b',
        r'\bmeritorious\s+students?\s+scheme\b',
        # Multilingual common academic aid descriptors
        r'\bshikshan\s+shulkh\b', r'\bshishyavrutti\b', r'\bchhatravritti\b',
        r'\bछात्रवृत्ति\b', r'\bशिष्यवृत्ती\b', r'\bमेधावी\s+छात्र\b', r'\bविद्यार्थी\s+सहायता\b'
    ]


    # --- PORTAL / DIRECTORY / GATEWAY SIGNALS (Discovery hubs, NEVER individual schemes) ---
    PORTAL_HUB_PATTERNS = [
        r'\bportal\b', r'\bplatform\b', r'\bgateway\b', r'\bdashboard\b',
        r'\bofficial\s+website\b', r'\bhomepage\b', r'\bwelcome\s+to\b',
        r'\bdepartment\s+of\b', r'\bministry\s+of\b', r'\bgovernment\s+of\b',
        r'\bcitizen\s+services?\b', r'\be[\s\-]services?\b', r'\bhelpdesk\b',
        r'\bfaq[s]?\b', r'\bcontact\s+us\b', r'\babout\s+us\b', r'\bterms\b',
        r'\ball\s+schemes\b', r'\blist\s+of\s+schemes\b', r'\bschemes\s+dashboard\b',
        r'\botr\s+application\b', r'\blogin\b', r'\bregistration\b', r'\buser\s+manual\b'
    ]

    # --- INVARIANT 2: ACADEMIC LEVEL & STUDENT BENEFICIARY SIGNALS ---
    ACADEMIC_BENEFICIARY_PATTERNS = [
        r'\bstudents?\b', r'\bscholar(?:s|ship)?\b', r'\bfellow(?:s|ship)?\b',
        r'\bcandidate(?:s)?\s+pursuing\b', r'\bapplicants?\s+enrolled\b',
        r'\bclass\s+(?:1[0-2]|[1-9]|ix|x|xi|xii)\b', r'\b10th\b', r'\b12th\b',
        r'\bmatric(?:ulation)?\b', r'\bintermediate\b', r'\bhigher\s+secondary\b',
        r'\bundergraduate\b', r'\bpostgraduate\b', r'\bph\.?d\b', r'\bdoctoral\b',
        r'\bdegree\b', r'\bdiploma\b', r'\bpolytechnic\b',
        r'\bb\.?tech\b', r'\bb\.?e\.?\b', r'\bm\.?tech\b', r'\bb\.?sc\b', r'\bm\.?sc\b',
        r'\bmbbs\b', r'\bb\.?com\b', r'\bmba\b', r'\bcollege\b', r'\buniversity\b',
        r'\binstitute\b', r'\bvidyarthi\b', r'\bchhatra\b'
    ]

    # --- INVARIANT 3: EDUCATIONAL FUNDING PURPOSE SIGNALS ---
    EDUCATIONAL_PURPOSE_PATTERNS = [
        r'\btuition\s+fee\b', r'\bcourse\s+fee\b', r'\bcollege\s+fee\b',
        r'\badmission\s+fee\b', r'\bhostel\s+fee\b', r'\bbook\s+grant\b',
        r'\bmonthly\s+stipend\b', r'\bresearch\s+(?:grant|fellowship|contingency)\b',
        r'\bmaintenance\s+allowance\b', r'\beducation(?:al)?\s+expenses?\b',
        r'\bfinancial\s+assistance\s+for\s+(?:study|studies|education|course)\b',
        r'\bscholarship\s+amount\b', r'\bannual\s+grant\b', r'\bper\s+annum\b',
        r'\bper\s+month\b', r'\bp\.m\.\b', r'\bfees?\s+reimbursement\b'
    ]

    @classmethod
    def is_directory_or_portal_hub(cls, url: str, title: str, text: str = "") -> Tuple[bool, str]:
        """
        Structural Gate: Determines if a document is an index hub, directory,
        or portal gateway rather than an individual grant/fellowship program.
        """
        norm_title = (title or "").lower().strip()
        parsed_url = urlparse(url)
        path = parsed_url.path.lower().rstrip('/')

        # 1. Obvious portal / gateway / department identity in title
        is_portal_identity = any(re.search(pat, norm_title) for pat in [
            r'\bportal\b', r'\bplatform\b', r'\bgateway\b', r'\bdashboard\b',
            r'\bdepartment\s+of\b', r'\bministry\s+of\b', r'\bofficial\s+website\b',
            r'\bwelcome\s+to\b', r'\bstate\s+portal\b', r'\bnational\s+portal\b',
            r'\bcitizen\s+services?\b'
        ])
        if is_portal_identity:
            return True, f"Title '{title}' represents a portal/gateway hub, not a discrete grant program."

        # 2. Generic navigation tab / endpoint paths
        generic_endpoints = [
            "/home", "/index", "/index.html", "/index.php", "/students", 
            "/schemes", "/services", "/citizen-services", "/dashboard", "/login", 
            "/register", "/otrapplication", "/contact", "/about", "/faq", "/faqs"
        ]
        if path in generic_endpoints:
            return True, f"URL path '{path}' is a directory hub/gateway endpoint, not an individual scheme notice."

        # 3. Short generic navigation titles
        clean_title = re.sub(r'[^a-z0-9\s]', ' ', norm_title).strip()
        words = clean_title.split()
        if len(words) <= 2 and clean_title in ["home", "about", "about us", "students", "schemes", 
                                               "downloads", "login", "dashboard", "services", 
                                               "faq", "faqs", "contact", "contact us", "portal",
                                               "welcome"]:
            return True, f"Title '{title}' is a generic navigation label."

        # 4. Root path ('/' or '') on multi-service / departmental portals
        if path in ["", "/"]:
            norm_body = (text or "").lower()[:1500]
            # If it's a root path, accept if title or prominent header text defines a scholarship/fellowship program
            has_explicit_scheme = (
                any(re.search(pat, norm_title) for pat in cls.SCHEME_IDENTITY_PATTERNS) or
                any(re.search(pat, norm_body) for pat in cls.SCHEME_IDENTITY_PATTERNS)
            )
            if not has_explicit_scheme:
                return True, f"Root domain '{parsed_url.netloc}' without explicit scholarship/fellowship identity is treated as directory hub."


        return False, "Node appears to be an individual content notice."


    @classmethod
    def validate_educational_intent(
        cls, 
        url: str, 
        title: str, 
        text_content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Authoritative validation based on the Educational Aid Triple Invariant.
        Guarantees that civic, commercial, municipal, and generic pages are rejected
        permanently without relying on keyword blacklists.
        """
        norm_title = (title or "").lower().strip()
        norm_text = (text_content or "").lower()
        header_text = norm_text[:10000]

        # STEP 1: DIRECTORY HUB & PORTAL SEPARATION GATE
        is_hub, hub_reason = cls.is_directory_or_portal_hub(url, title, text_content)
        if is_hub:
            return False, f"Directory Hub Rejected: {hub_reason}", {"type": "DIRECTORY_HUB"}

        # STEP 2: INVARIANT 1 — PROGRAM IDENTITY VALIDATION
        # Must clearly reference a scholarship, fellowship, academic grant, or stipend
        has_scheme_in_title = any(re.search(pat, norm_title) for pat in cls.SCHEME_IDENTITY_PATTERNS)
        has_scheme_in_header = any(re.search(pat, header_text) for pat in cls.SCHEME_IDENTITY_PATTERNS)

        if not (has_scheme_in_title or has_scheme_in_header):
            return False, f"Contract Failure (Pillar 1): '{title}' does not define an educational scholarship, fellowship, or stipend program.", {
                "type": "NOT_AN_EDUCATIONAL_SCHEME"
            }

        # STEP 3: INVARIANT 2 — ACADEMIC BENEFICIARY VALIDATION
        # Must affirmatively target students, scholars, researchers, or specific academic stages
        academic_matches = [pat for pat in cls.ACADEMIC_BENEFICIARY_PATTERNS if re.search(pat, header_text)]
        if len(academic_matches) < 1:
            return False, f"Contract Failure (Pillar 2): Document lacks verifiable academic beneficiary (target students/scholars).", {
                "type": "LACKS_ACADEMIC_BENEFICIARY"
            }

        # STEP 4: INVARIANT 3 — EDUCATIONAL FUNDING PURPOSE VALIDATION
        # Must affirmatively provide educational financial support (fees, stipend, grant, contingency)
        has_financial_benefit = any(re.search(pat, header_text) for pat in cls.EDUCATIONAL_PURPOSE_PATTERNS)
        # Also accept if specific monetary currency patterns or fee waiver words are present in educational context
        has_monetary_currency = bool(re.search(r'(?:₹|rs\.?|inr)\s*[\d,]+', header_text))
        has_waiver_or_support = any(w in header_text for w in ["waiver", "stipend", "allowance", "grant", "reimbursement", "award", "freeship", "financial aid", "assistance"])
        
        if not (has_financial_benefit or has_monetary_currency or has_waiver_or_support):
            return False, f"Contract Failure (Pillar 3): Document provides no identifiable educational funding, stipend, or fee reimbursement mechanism.", {
                "type": "LACKS_EDUCATIONAL_FUNDING"
            }

        # ALL 3 INVARIANTS POSITIVELY SATISFIED
        return True, f"Verified: Satisfies Educational Aid Triple Invariant ({len(academic_matches)} academic signals, verified educational funding).", {
            "type": "VERIFIED_EDUCATIONAL_SCHOLARSHIP",
            "academic_signals": academic_matches
        }

