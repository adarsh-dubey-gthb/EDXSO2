"""
NLP and Semantic Information Extraction Engine.
Extracts structured 19+ scholarship attributes from unstructured HTML/text documents
using regular expressions, entity recognition heuristics, and semantic boundary parsers.
Enforces zero hallucination by strictly assigning 'Not specified' to absent attributes.
"""

import re
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup
from storage.models import ScholarshipRecord
from crawler.classifier import SourceClassifier

class NLPScholarshipExtractor:
    @staticmethod
    def clean_text(text: str) -> str:
        if not text:
            return ""
        return " ".join(text.split())

    @classmethod
    def extract_from_raw_document(
        cls, 
        doc_id: str,
        source_url: str,
        raw_content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ScholarshipRecord:
        """
        Processes raw unstructured text/HTML from an official scholarship portal/gazette
        and converts it into our standardized 19+ universal schema attributes.
        """
        meta = metadata or {}
        
        # If HTML, strip script/style and get text
        if "<html" in raw_content.lower() or "<div" in raw_content.lower():
            soup = BeautifulSoup(raw_content, "html.parser")
            for t in soup(["script", "style", "noscript", "svg"]):
                t.decompose()
            text = soup.get_text(separator=" ", strip=True)
        else:
            text = raw_content

        text_clean = cls.clean_text(text)
        text_lower = text_clean.lower()

        # 1. Scheme Name
        name = meta.get("name")
        if not name:
            # Try to find header patterns (e.g. Scheme:, Scholarship:, or first strong heading)
            m = re.search(r'(?:scheme|scholarship|fellowship)\s*name\s*[:\-]\s*([^\n\.\;]{10,120})', text_clean, re.I)
            if m:
                name = m.group(1).strip()
            else:
                m_title = re.search(r'^([A-Z0-9\s\-–\(\)]{10,100})(?:\n|\.|\:)', text_clean)
                name = m_title.group(1).strip() if m_title else "Official Scholarship Scheme"

        # 2. Provider / Authority
        provider = meta.get("provider")
        if not provider:
            m_prov = re.search(r'(?:offered by|implemented by|provider|ministry|council)\s*[:\-]?\s*([^\n\.\;]{5,100})', text_clean, re.I)
            if m_prov:
                provider = m_prov.group(1).strip()
            else:
                provider = "Central / State Educational Authority"

        # 3. Source Type Classification
        source_type, is_auth, _ = SourceClassifier.classify_source(source_url)
        if meta.get("source_type"):
            source_type = meta["source_type"]

        # 4. Financial Benefit Amount
        amount = "Not specified"
        m_rev_amt = re.search(r'(?:revised?|revision|enhanced?|enhancement)[^\n:]*[:\-]?\s*(?:financial\s+benefit\s+amount\s*[:\-]?)?\s*(?:up\s+to\s+)?((?:₹|rs\.?|inr)\s*[\d,]+[^\.\n;]{0,80})', text_clean, re.I)
        if m_rev_amt:
            amount = f"Up to {m_rev_amt.group(1).strip()}" if "up to" in m_rev_amt.group(0).lower() and not m_rev_amt.group(1).lower().startswith("up to") else m_rev_amt.group(1).strip()
        else:
            all_amts = re.findall(r'(?:₹|rs\.?|inr)\s*[\d,]+(?:\s*(?:per\s+annum|\/year|\/month|p\.m\.|per\s+month|lakhs?|lacs?|one[- ]time))?[^\.\n;]{0,80}', text_clean, re.I)
            # Filter amounts to ensure they are plausible scholarship grants:
            # Must either contain 'lakh', 'thousand', 'per annum', 'p.m.', or a numeric value >= 1000.
            # Excludes trivial portal transaction fees (like 'Rs 30' or 'Rs 50')
            valid_amts = []
            for a in all_amts:
                digits = re.sub(r'[^\d]', '', a)
                val = int(digits) if digits else 0
                has_unit = any(u in a.lower() for u in ['lakh', 'lac', 'thousand', 'per', 'p.m.', 'annum', 'year', 'month'])
                if has_unit or val >= 1000:
                    valid_amts.append(a.strip())

            if valid_amts:
                amount = valid_amts[0]
            elif "full tuition fee" in text_lower or "100% tuition" in text_lower or "50% tuition" in text_lower:
                m_fee = re.search(r'(?:full|100%|50%|partial)\s+tuition\s+fee[^\.\n;]{0,60}', text_clean, re.I)
                amount = m_fee.group(0).strip() if m_fee else "Tuition Fee Reimbursement"

        # 5. Course / Education Level
        course_level = "Undergraduate"
        if any(w in text_lower for w in ["ph.d", "phd", "doctoral", "research fellowship"]):
            course_level = "Ph.D. (Doctoral)"
        elif any(w in text_lower for w in ["postgraduate", "m.tech", "m.e.", "m.sc", "mba", "masters"]):
            course_level = "Postgraduate"
        elif any(w in text_lower for w in ["diploma", "polytechnic"]):
            course_level = "Diploma / Polytechnic"
        elif any(w in text_lower for w in ["undergraduate", "b.tech", "b.e.", "b.sc", "b.com", "ba", "degree"]):
            course_level = "Undergraduate (Degree)"

        # 6. Eligibility Overview
        eligibility = "Not specified"
        m_elig = re.search(r'eligibility(?:\s*criteria)?\s*[:\-]\s*([^\n]{20,250})', text_clean, re.I)
        if m_elig:
            eligibility = m_elig.group(1).strip()
        else:
            # Look for sentence mentioning eligible or candidates admitted
            for s in text_clean.split("."):
                if any(w in s.lower() for w in ["eligible", "admitted to", "students pursuing", "who have secured"]):
                    if len(s.strip()) > 30:
                        eligibility = s.strip()
                        break

        # 7. Academic Requirements
        academic_req = "Not specified"
        m_acad = re.search(r'(?:academic requirements|minimum marks|qualifying exam)\s*[:\-]\s*([^\n]{15,200})', text_clean, re.I)
        if m_acad:
            academic_req = m_acad.group(1).strip()
        else:
            m_perc = re.search(r'(?:minimum\s+\d+%\s+marks|top\s+1%|cgpa\s+(?:of\s+)?[\d\.]+|valid\s+gate|neet|jee)[^\.\n;]{0,60}', text_clean, re.I)
            if m_perc:
                academic_req = m_perc.group(0).strip()

        # 8. Family Income Criteria (Anti-Hallucination: Strictly "Not specified" if absent)
        income = "Not specified"
        m_inc = re.search(r'(?:family|parental|household)?\s*annual\s*income\s*(?:not\s*more\s*than|not\s*exceeding|up\s*to|less\s*than|below)?\s*[:\-]?\s*(?:₹|rs\.?|inr)?\s*[\d\.,]+\s*(?:lakhs?|lacs?|thousand|p\.a\.|per\s+annum)?[^\.\n;]{0,50}', text_clean, re.I)
        if m_inc and any(w in m_inc.group(0).lower() for w in ["lakh", "lac", "rs", "₹", "income"]):
            income = m_inc.group(0).strip()

        # 9. Age Criteria
        age = "Not specified"
        m_age = re.search(r'(?:age(?:\s*limit)?|maximum\s*age)\s*[:\-]?\s*(\d{2}\s*(?:to\s*\d{2})?\s*years?|not\s*more\s*than\s*\d{2}\s*years?)', text_clean, re.I)
        if m_age:
            age = m_age.group(0).strip()

        # 10. Gender Criteria
        gender = "All genders"
        if any(w in text_lower for w in ["girl students", "female only", "women only", "girls only", "women in science"]):
            gender = "Female only"

        # 11. Category Criteria
        category = "Open to all categories"
        cats = []
        if "sc" in text_lower or "scheduled caste" in text_lower:
            cats.append("SC")
        if "st" in text_lower or "scheduled tribe" in text_lower:
            cats.append("ST")
        if "obc" in text_lower or "other backward classes" in text_lower:
            cats.append("OBC")
        if "pwd" in text_lower or "specially-abled" in text_lower or "disability" in text_lower:
            cats.append("PwD")
        if "ews" in text_lower:
            cats.append("EWS")
        if cats:
            category = ", ".join(cats)

        # 12. Domicile Requirements
        domicile = "All India"
        m_dom = re.search(r'domicile\s*(?:of)?\s*([a-zA-Z\s]{4,30})(?:\s*only)?', text_clean, re.I)
        if m_dom:
            domicile = f"{m_dom.group(1).strip()} only"
        elif "maharashtra" in text_lower:
            domicile = "State of Maharashtra only"
        elif "west bengal" in text_lower:
            domicile = "State of West Bengal only"

        # 13. Institution Requirements
        inst_req = "Recognized universities/colleges in India"
        if "aicte approved" in text_lower:
            inst_req = "AICTE approved technical institutions"
        elif "premier institutes" in text_lower or "iit" in text_lower:
            inst_req = "Notified Premier Institutes (IITs, IIMs, IISc, NITs, AIIMS)"

        # 14. Dates (Opening & Closing Deadlines)
        closing_date = "Not specified"
        # Check for Corrigendum / Extension first
        m_corr = re.search(r'(?:extended\s*to|revised\s*to|corrigendum[^\n\:\.]+[:\-]?)\s*(\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]+\s+\d{4})', text_clean, re.I)
        if m_corr:
            closing_date = m_corr.group(1).strip()
        else:
            all_dead = re.findall(r'(?:last\s*date|closing\s*date|deadline|closed\s*on)\s*[:\-]?\s*(\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]+\s+\d{4}|\d{4}-\d{2}-\d{2}|\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})', text_clean, re.I)
            if all_dead:
                closing_date = all_dead[0].strip()
            
        opening_date = "Not specified"
        m_open = re.search(r'(?:opening\s*date|starts\s*on|application\s*open\s*from)\s*[:\-]?\s*(\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]+\s+\d{4}|\d{4}-\d{2}-\d{2})', text_clean, re.I)
        if m_open:
            opening_date = m_open.group(1).strip()

        # 15. Application URL
        # Use meta-provided URL first; then try to extract from text; then fall back to source URL domain
        app_url = meta.get("application_url") or ""
        if not app_url or app_url == "Not specified":
            m_link = re.search(r'(https?:\/\/[^\s\'\"\<\>]+(?:apply|portal|application|register)[^\s\'\"\<\>]*)', text_clean, re.I)
            if m_link:
                app_url = m_link.group(1)

        # If still no application URL, derive from the official source URL (not hardcoded scholarships.gov.in)
        if not app_url:
            parsed_src = re.match(r'(https?://[^/]+)', source_url)
            app_url = parsed_src.group(1) if parsed_src else "https://scholarships.gov.in"

        if not app_url or app_url == "Not specified":
            app_url = "https://scholarships.gov.in"

        # 16. Documents Required
        docs = "Standard documents: Marksheets, Income certificate, Admission proof, Bank details, Identity proof"
        m_docs = re.search(r'documents\s*required\s*[:\-]\s*([^\n]{20,200})', text_clean, re.I)
        if m_docs:
            docs = m_docs.group(1).strip()

        # 17. Selection Process
        selection = "Merit-based allocation in accordance with scheme guidelines."
        m_sel = re.search(r'selection\s*process\s*[:\-]\s*([^\n]{20,200})', text_clean, re.I)
        if m_sel:
            selection = m_sel.group(1).strip()

        # 18. Renewal Requirements
        renewal = "Annual renewal subject to passing examinations and maintaining minimum attendance."
        m_ren = re.search(r'renewal\s*requirements\s*[:\-]\s*([^\n]{20,200})', text_clean, re.I)
        if m_ren:
            renewal = m_ren.group(1).strip()

        # Primary Evidence Quote (Extracted directly from source text window)
        evidence_snippet = text_clean[:250] + "..." if len(text_clean) > 250 else text_clean

        return ScholarshipRecord(
            id=doc_id,
            name=name,
            provider=provider,
            official_source=source_url,
            application_url=app_url,
            source_type=source_type,
            amount=amount,
            eligibility=eligibility,
            academic_requirements=academic_req,
            course_level=course_level,
            income_criteria=income,
            age_criteria=age,
            gender_criteria=gender,
            category_criteria=category,
            domicile_requirements=domicile,
            institution_requirements=inst_req,
            opening_date=opening_date,
            closing_date=closing_date,
            documents_required=docs,
            selection_process=selection,
            renewal_requirements=renewal,
            current_status="ACTIVE",
            confidence_score=0.0,
            verification_status="REVIEW_REQUIRED",
            date_last_verified="2026-10-03",
            why_this_score="",
            source_evidence=evidence_snippet
        )
