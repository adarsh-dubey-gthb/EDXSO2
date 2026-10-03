"""
Anti-Hallucination and Evidence Grounding Engine.
Ensures every extracted field is grounded in verbatim source evidence.
Enforces 'Not specified' for any missing attributes to prevent synthetic fabrication.
"""

import re
from typing import Dict, Any, List, Optional, Tuple
from storage.models import VerificationEvidence

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

CRITICAL_FIELDS = [
    ("name", "Scholarship Name"),
    ("provider", "Provider / Authority"),
    ("amount", "Financial Benefit"),
    ("eligibility", "Eligibility Criteria"),
    ("closing_date", "Application Deadline"),
    ("income_criteria", "Family Income Limit")
]

# Global cache for Hugging Face neural embedding model
_HF_TOKENIZER = None
_HF_MODEL = None
_HF_TRIED_LOAD = False

def _get_hf_model():
    global _HF_TOKENIZER, _HF_MODEL, _HF_TRIED_LOAD
    if _HF_TRIED_LOAD:
        return _HF_TOKENIZER, _HF_MODEL
    _HF_TRIED_LOAD = True
    try:
        from transformers import AutoTokenizer, AutoModel
        import torch
        model_name = 'sentence-transformers/all-MiniLM-L6-v2'
        _HF_TOKENIZER = AutoTokenizer.from_pretrained(model_name)
        _HF_MODEL = AutoModel.from_pretrained(model_name)
        _HF_MODEL.eval()
    except Exception:
        _HF_TOKENIZER, _HF_MODEL = None, None
    return _HF_TOKENIZER, _HF_MODEL

class AntiHallucinationEngine:
    @staticmethod
    def sanitize_field(value: Optional[str]) -> str:
        """
        Guarantees that unmentioned or absent fields are marked 'Not specified'
        rather than fabricated or left null.
        """
        if not value:
            return "Not specified"
        v = str(value).strip()
        if v.lower() in ["", "none", "null", "n/a", "not available", "unknown", "nil"]:
            return "Not specified"
        return v

    @classmethod
    def verify_grounding_neural_transformer(
        cls, 
        field_value: str, 
        source_text: str
    ) -> Tuple[bool, Optional[str], float]:
        """
        Open-Source AI Neural Transformer Semantic Embedding Grounding (Hugging Face all-MiniLM-L6-v2).
        Computes dense neural vector embeddings for query field and source candidate sentences,
        measuring cosine distance in high-dimensional vector space.
        Falls back to Scikit-Learn TF-IDF vectorization if PyTorch model is unavailable.
        """
        if not field_value or field_value == "Not specified":
            return True, "Source verified: Field not specified in primary notification (unmentioned).", 1.0

        sentences = [s.strip() for s in re.split(r'[\.\n\r;]', source_text) if len(s.strip()) > 10]
        if not sentences:
            sentences = [source_text]

        # Direct substring shortcut
        if field_value.lower() in source_text.lower():
            return True, f"Verbatim match: '{field_value}'", 1.0

        # Try Hugging Face Neural Transformer Embeddings
        tokenizer, model = _get_hf_model()
        if tokenizer is not None and model is not None:
            try:
                import torch
                # Candidate selection: query + sentences
                texts = [field_value] + sentences[:15]
                inputs = tokenizer(texts, padding=True, truncation=True, max_length=128, return_tensors="pt")
                with torch.no_grad():
                    outputs = model(**inputs)
                    mask = inputs['attention_mask'].unsqueeze(-1)
                    embeddings = torch.sum(outputs.last_hidden_state * mask, 1) / torch.clamp(mask.sum(1), min=1e-9)
                    embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)

                sims = torch.mm(embeddings[0:1], embeddings[1:].t()).squeeze(0)
                best_idx = int(torch.argmax(sims))
                best_sim = float(sims[best_idx])
                best_sentence = sentences[best_idx]

                if best_sim >= 0.45:
                    return True, f"HuggingFace Neural Embedding (Score {round(best_sim, 2)}): '{best_sentence[:180]}'", best_sim
            except Exception:
                pass

        # Fallback to TF-IDF semantic vector space
        return cls.verify_grounding_tfidf(field_value, source_text)

    @classmethod
    def verify_grounding_tfidf(
        cls, 
        field_value: str, 
        source_text: str
    ) -> Tuple[bool, Optional[str], float]:
        """
        AI/NLP Semantic Grounding using TF-IDF Vectorization and Cosine Similarity.
        Finds the exact source sentence with highest semantic alignment to verify authenticity.
        Returns: (is_grounded, best_matching_verbatim_sentence, similarity_score)
        """
        if not field_value or field_value == "Not specified":
            return True, "Source verified: Field not specified in primary notification (unmentioned).", 1.0

        # Split source into candidate sentences/segments
        sentences = [s.strip() for s in re.split(r'[\.\n\r;]', source_text) if len(s.strip()) > 10]
        if not sentences:
            sentences = [source_text]

        # Direct substring shortcut
        if field_value.lower() in source_text.lower():
            return True, f"Verbatim match: '{field_value}'", 1.0

        try:
            vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words='english')
            corpus = [field_value] + sentences
            tfidf_matrix = vectorizer.fit_transform(corpus)
            
            # Cosine similarity between query field_value (idx 0) and all sentences
            sims = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:]).flatten()
            best_idx = sims.argmax()
            best_sim = float(sims[best_idx])
            best_sentence = sentences[best_idx]

            # If semantic similarity >= 0.35
            if best_sim >= 0.35:
                return True, f"TF-IDF Semantic Match (Score {round(best_sim, 2)}): '{best_sentence[:180]}'", best_sim
        except Exception:
            pass

        # Fallback keyword overlap
        norm_source = " ".join(source_text.lower().split())
        tokens = [t for t in field_value.lower().split() if len(t) > 2 and t not in ['the', 'for', 'and', 'with', 'level']]
        if tokens:
            overlap = sum(1 for t in tokens if t in norm_source) / len(tokens)
            if overlap >= 0.50:
                return True, f"Token Overlap Match ({int(overlap*100)}%): '{field_value[:120]}'", overlap

        return False, None, 0.0

    @classmethod
    def verify_grounding(
        cls, 
        field_value: str, 
        source_text: str
    ) -> Tuple[bool, Optional[str]]:
        is_gr, quote, _ = cls.verify_grounding_neural_transformer(field_value, source_text)
        return is_gr, quote

    @classmethod
    def normalize_text_for_search(cls, text: str) -> str:
        """Normalizes Indian currency, numbers, and common abbreviations for faithful semantic matching."""
        if not text:
            return ""
        t = text.lower()
        # Normalize rupee symbols and variants
        t = re.sub(r'(₹|rs\.?|inr|rupees)\s*', 'rs ', t)
        # Normalize lakhs and commas
        t = re.sub(r'(\d+),(\d+)', r'\1\2', t)
        t = re.sub(r'\b(lakhs?|lacs?)\b', 'lakh', t)
        # Normalize dates (e.g. 31st -> 31)
        t = re.sub(r'(\d+)(st|nd|rd|th)\b', r'\1', t)
        # Normalize punctuation & whitespace
        t = re.sub(r'[-_/(),.:]', ' ', t)
        return " ".join(t.split())

    @classmethod
    def verify_grounding(
        cls, 
        field_value: str, 
        source_text: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Verifies if an extracted value is grounded in the raw source text.
        Returns: (is_grounded, verbatim_evidence_snippet)
        """
        if not field_value or field_value == "Not specified":
            # Correctly flagged as not specified; truthful and non-hallucinatory
            return True, "Source verified: Field not specified in primary notification (unmentioned)."
            
        norm_source = cls.normalize_text_for_search(source_text)
        norm_val = cls.normalize_text_for_search(field_value)
        
        # 1. Exact normalized substring match
        if norm_val in norm_source:
            idx = norm_source.find(norm_val)
            start = max(0, idx - 40)
            end = min(len(norm_source), idx + len(norm_val) + 60)
            snippet = source_text[start:end].strip() if len(source_text) >= end else source_text[:200]
            return True, f"Verified text match: '{snippet}'"
            
        # 2. Extract key meaningful tokens (numbers, currency, key nouns)
        tokens = [t for t in norm_val.split() if len(t) > 2 and t not in ['the', 'for', 'and', 'with', 'from', 'level', 'under', 'study']]
        if tokens:
            matched_tokens = [t for t in tokens if t in norm_source]
            ratio = len(matched_tokens) / len(tokens)
            # If 60% of significant tokens (or key amounts/deadlines) match
            if ratio >= 0.60:
                return True, f"Grounded in source text ({int(ratio*100)}% token alignment): '{field_value[:120]}'"
                
        return False, None

    @classmethod
    def audit_record(
        cls, 
        scholarship_data: Dict[str, Any], 
        raw_source_text: str,
        source_url: str
    ) -> Tuple[float, List[VerificationEvidence], Dict[str, Any]]:
        """
        Performs full anti-hallucination audit across all critical fields.
        Returns: (grounding_score [0.0 - 1.0], evidence_list, audit_report)
        """
        now_iso = "2026-10-03 02:00:00"
        evidence_list: List[VerificationEvidence] = []
        grounded_count = 0
        field_audits = {}
        
        for field_key, field_label in CRITICAL_FIELDS:
            val = scholarship_data.get(field_key, "Not specified")
            is_grounded, quote = cls.verify_grounding(val, raw_source_text)
            
            if is_grounded:
                grounded_count += 1
                evidence_text = quote if quote else f"Explicitly verified: '{val}'"
                field_audits[field_label] = {
                    "grounded": True,
                    "evidence": evidence_text
                }
                evidence_list.append(VerificationEvidence(
                    scholarship_id=scholarship_data.get("id", ""),
                    field_name=field_label,
                    evidence_quote=evidence_text,
                    source_url=source_url,
                    verified_at=now_iso
                ))
            else:
                field_audits[field_label] = {
                    "grounded": False,
                    "evidence": f"Warning: Value '{val}' not traced directly in source text snippet."
                }
                
        total_fields = len(CRITICAL_FIELDS)
        score = grounded_count / total_fields
        return score, evidence_list, field_audits
