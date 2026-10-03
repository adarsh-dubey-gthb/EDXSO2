# TECHNICAL NOTE: SCHOLARSHIP INTELLIGENCE CRAWLER
**Atlas Funding Architecture & Verification Engine**  
*Target System:* Autonomous Multi-Source Scholarship Ingestion, Verification, and Change Tracking Engine for Indian Students  

---

## 1. System Architecture

The Scholarship Intelligence Crawler is designed as an autonomous, modular intelligence pipeline operating across seven deterministic stages:

```
[ Seed Portals ] 
       │
       ▼
1. Dynamic Discovery  ──▶  Traverses seed portals, extracts candidate scheme links, filters static assets
       │
       ▼
2. Source Classification ─▶ Distinguishes Primary Authority (.gov.in, .nic.in, .ac.in, CSR) from Aggregators
       │
       ▼
3. Normalization & Extraction ─▶ Maps raw content into 19+ universal schema fields; strictly sanitizes missing fields
       │
       ▼
4. Verification & Grounding ─▶ Domain authenticity validation, HTTP liveness, verbatim source text grounding
       │
       ▼
5. Confidence Engine  ──▶ Deterministic multi-factor mathematical scoring (>=95% VERIFIED, else REVIEW REQUIRED)
       │
       ▼
6. Storage & Lifecycle ──▶ SQLite storage; evaluates ACTIVE, EXPIRING_SOON, EXPIRED, NO_LONGER_VERIFIABLE
       │
       ▼
7. Change Detection  ──▶ Compares against prior state snapshots; logs delta audit entries without overwriting
```

### Core Architecture Components:
1. **Fetcher & Discovery Engine (`crawler/fetcher.py`, `crawler/discovery.py`)**: Handles HTTP pooling, Indian PKI/NIC SSL tolerance, recursive hyperlink discovery, and anchor keyword heuristics.
2. **Domain & Source Classifier (`crawler/classifier.py`, `verification/domain_verifier.py`)**: Classifies candidate links into Central Government, State Government, Statutory Bodies, Corporate CSR, Premier Universities, or Aggregators.
3. **Structured Extractor (`crawler/extractor.py`)**: Converts unstructured HTML/notifications into structured 19+ field records (`storage/models.py`).
4. **Anti-Hallucination & Evidence Engine (`verification/anti_hallucination.py`)**: Implements field-level quote tracing (`Database -> Official Source -> Verbatim Quote -> Extracted Value`) and enforces the "Not specified" rule.
5. **Deterministic Confidence Engine (`verification/confidence_engine.py`)**: Calculates transparent scores without LLM guess-work and generates "Why this score?" explainability logs.
6. **Change & Stale-Data Engine (`change_detection/tracker.py`)**: Detects field modifications across crawl cycles, manages lifecycle transitions, and stores timestamped audit diffs.
7. **Persistence Layer (`storage/database.py`)**: Normalized SQLite relational schema (`scholarships`, `verification_evidence`, `change_history`, `crawl_runs`, `discovered_seeds`).
8. **Operations Dashboard (`ui/app.py`)**: Real-time Streamlit dashboard providing search, metric cards, field inspectors, and live crawler triggering.

---

## 2. Technology Choices & Justification

To ensure a 100% self-hosted, cost-effective infrastructure without reliance on paid scraping APIs:

| Technology | Role | Justification |
| :--- | :--- | :--- |
| **Python 3.12** | Core Runtime | Universal language with rich web automation, data parsing, and string processing ecosystems. |
| **Hugging Face Transformers & PyTorch** | Neural Semantic AI | Open-source embedding model (`all-MiniLM-L6-v2`) projecting gazette text and extracted attributes into 384-dimensional vector space for anti-hallucination verification. |
| **Scikit-Learn NLP** | Semantic Similarity | Sub-word n-gram TF-IDF vectorization and cosine similarity matrix calculations for evidence grounding. |
| **SQLite 3** | Database Engine | Zero-dependency, serverless, atomic ACID relational database enabling instant portability, zero cloud cost, and direct file inspection. |
| **Requests & Urllib3** | Network Transport | Connection-pooled HTTP client with custom header emulation and SSL exception handlers for Indian NIC/Gov CA roots. |
| **BeautifulSoup 4** | HTML Parser | Resilient DOM traversal, navigation, script stripping, and text extraction from imperfect government HTML. |
| **Streamlit** | Dashboard Interface | Modern, reactive, pure-Python UI allowing interactive exploration of KPI metrics, search filtering, evidence inspection, and live crawler triggers. |
| **Deterministic Heuristic Formulation** | Confidence Guardrail | Replaces black-box non-deterministic LLM confidence hallucination with transparent, mathematically explainable verification. |

Paid scraping APIs (ScraperAPI, BrightData, ProxyMesh) and commercial LLMs (OpenAI, Anthropic) were deliberately excluded to ensure complete independence and reproducibility.

---

## 3. Discovery Methodology

Unlike hard-coded one-time scrapers (`URL 1 -> Scraper 1`), the system deploys an intelligent link traversal pipeline:

1. **Seed Ingestion**: The engine initiates from high-authority gateway portals across 5 sectors:
   - Central Portals: National Scholarship Portal (`scholarships.gov.in`), DST INSPIRE (`online-inspire.gov.in`)
   - Statutory Councils: AICTE (`aicte-india.org`), UGC / NTA (`ugcnet.nta.ac.in`)
   - Corporate CSR Foundations: Reliance Foundation (`scholarships.reliancefoundation.org`), Tata Trusts (`tatatrusts.org`), ONGC Foundation (`ongcscholar.org`)
   - Premier Institutions: PMRF (`pmrf.in`), IISc Bangalore (`iisc.ac.in`), IIT Delhi (`home.iitd.ac.in`)
   - State Portals: MahaDBT (`mahadbt.maharashtra.gov.in`), West Bengal OASIS (`oasis.gov.in`)
2. **Anchor & Path Semantic Heuristics**: The crawler evaluates hyperlinks using regex and semantic keyword matching (`scholarship`, `scheme`, `fellowship`, `grant`, `financial-support`, `pragati`, `saksham`, `yojana`, `stipend`).
3. **Source Classification**: Extracted URLs are parsed via `SourceClassifier.classify_source()`:
   - Recognizes authorized TLDs (`.gov.in`, `.nic.in`, `.ac.in`, `.edu.in`).
   - Validates official corporate foundations via domain registry matching.
   - Detects known aggregators (`buddy4study.com`, `shiksha.com`) and tags them as secondary discovery sources only.
4. **Open-Web Dynamic Discovery & Live URL Ingestion**:
   - **Beyond Fixed Seeds**: Integrates free open-source search (`duckduckgo_search` / `ddgs`) to dynamically query the live web for scholarship announcements and official notifications.
   - **Interactive Live Ingestion**: Exposes `ScholarshipPipeline.crawl_and_ingest_url()` via both CLI (`python run_crawler.py --crawl-url <URL>`) and the Streamlit UI, allowing users to input any live web URL and observe real-time HTTP fetching, source classification, NLP extraction, deterministic confidence scoring, and database persistence.

---

## 4. Extraction Methodology

The system parses unstructured announcements, gazettes, and portal pages into the standardized 19+ field schema required by Atlas Funding:

- **Entity Identification**: `name`, `provider`, `source_type`.
- **Authoritative URLs**: `official_source`, `application_url`.
- **Financial & Academic Benefits**: `amount` (normalized across lump-sums, monthly stipends, and tuition fee waivers).
- **Eligibility Criteria**: `eligibility`, `academic_requirements`, `course_level`.
- **Socio-Economic Thresholds**: `income_criteria` (normalized into standard Lakh ceilings), `age_criteria`, `gender_criteria`, `category_criteria` (SC/ST/OBC/General/EWS/PwD), `domicile_requirements`, `institution_requirements`.
- **Operational Timeline & Logistics**: `opening_date`, `closing_date`, `documents_required`, `selection_process`, `renewal_requirements`.
- **Lifecycle & Confidence Metrics**: `current_status`, `confidence_score`, `verification_status`, `date_last_verified`, `why_this_score`, `source_evidence`.

---

## 5. Verification Methodology

A core tenet of the system is that **accuracy takes precedence over quantity**. The verification engine applies a two-tiered validation:

1. **Authority Tiering**:
   - **Primary Authority (Tier 1)**: Official Government portals (`.gov.in`, `.nic.in`), statutory bodies (AICTE, UGC), accredited universities (`.ac.in`), and verified corporate foundation domains (`tatatrusts.org`, `scholarships.reliancefoundation.org`, `ongcscholar.org`).
   - **Secondary / Non-Authoritative (Tier 2)**: Commercial aggregators (`buddy4study.com`, `collegedunia.com`). These are permitted for link discovery but are strictly prohibited as primary sources.
2. **Liveness & Integrity Probing**:
   - Executes live HTTP probing to verify that the official source returns `HTTP 200`.
   - Verifies that the official scheme title and key identity tokens exist directly within the live DOM content.
   - Verifies whether a valid, reachable application portal URL is provided.

---

## 6. Confidence-Score Methodology

To maintain deterministic auditability and prevent generative hallucinations, confidence scores are computed mathematically rather than queried from probabilistic LLMs:

$$\text{Confidence Score} = 100 \times \sum_{i=1}^{6} \left( w_i \times S_i \right) - P_{\text{conflict}}$$

Where weights $w_i$ sum to $1.00$:

| Factor ($S_i$) | Weight ($w_i$) | Mathematical Scoring Formulation |
| :--- | :---: | :--- |
| **Domain Authenticity** ($S_{\text{domain}}$) | **0.25** | $1.00$ for Gov/Academic portals; $0.96$ for verified CSR foundations; $0.00$ for aggregators; $0.25$ for unverified sites. |
| **Source Liveness** ($S_{\text{live}}$) | **0.20** | $1.00$ if live (HTTP 200) and scheme title confirmed in page text; $0.60$ if redirected; $0.00$ if error/unreachable. |
| **Application Portal Auth** ($S_{\text{app}}$) | **0.15** | $1.00$ if application URL is hosted on official domain; $0.75$ if secondary domain; $0.50$ if offline/in-person; $0.40$ if third-party. |
| **Evidence Grounding** ($S_{\text{evidence}}$) | **0.20** | Grounding ratio $\frac{\text{grounded critical fields}}{6}$ where fields are verified via verbatim substring or $\ge 60\%$ semantic token match. |
| **Temporal Freshness** ($S_{\text{temporal}}$) | **0.10** | $1.00$ for valid future deadlines; $0.95$ for verified expired schemes; $0.85$ for rolling schemes ("Not specified"). |
| **Schema Completeness** ($S_{\text{schema}}$) | **0.10** | Populated ratio $\frac{\text{present fields}}{8}$ across mandatory core fields. |

- **Conflict Penalty ($P_{\text{conflict}}$)**: Deducts $0.20$ if contradictory dates or amounts are detected across sources.
- **Classification Threshold**:
  $$\text{Status} = \begin{cases} \mathbf{VERIFIED} & \text{if } \text{Confidence Score} \ge 95.0\% \\ \mathbf{REVIEW\_REQUIRED} & \text{if } \text{Confidence Score} < 95.0\% \end{cases}$$

Every record generates an automated, human-auditable **"Why this score?"** breakdown stored in the database.

---

## 7. Anti-Hallucination Approach

To eliminate synthetic data fabrication:

1. **Strict "Not specified" Guarantee**: If an official document or portal does not explicitly state a parameter (such as an income ceiling or age limit), the system strictly assigns `"Not specified"`. It never guesses or infers arbitrary numbers.
2. **Field-Level Evidence Traceability**:
   Every critical attribute is saved with an explicit traceability chain:
   $$\text{Database Record} \longrightarrow \text{Official Source URL} \longrightarrow \text{Verbatim Evidence Quote} \longrightarrow \text{Extracted Value}$$
3. **Verbatim Text Anchoring**: The system stores exact source text snippets in the `verification_evidence` table. During manual audit, any field can be immediately compared against the exact official quote extracted by the crawler.

---

## 8. Change Detection & Stale-Data Management

The system operates as a continuous state-aware crawler rather than a one-time scraper:

1. **Delta Tracking**:
   During subsequent crawl runs (`Run 2`, `Run 3`), the engine compares the newly extracted values against the stored baseline across monitored fields (`closing_date`, `amount`, `eligibility`, `current_status`, `application_url`, `income_criteria`).
2. **Audit Trail Retention**:
   When a difference is detected, the engine **never silently overwrites** the old data. Instead, it inserts an immutable record into the `change_history` table:
   - `scholarship_id`
   - `field_name`
   - `old_value`
   - `new_value`
   - `date_detected`
   - `source`
   - `evidence`
3. **Lifecycle Status Automation**:
   - **`ACTIVE`**: Verified active scheme with deadline in the future ($> 14$ days).
   - **`EXPIRING_SOON`**: Active scheme with deadline within 14 days.
   - **`EXPIRED`**: Application window closed (deadline in past).
   - **`REVIEW_REQUIRED`**: Confidence $< 95\%$ or secondary source requiring human clearance.
   - **`NO_LONGER_VERIFIABLE`**: Source page returns HTTP 404/410 or notification withdrawn.

---

## 9. Contract-Based Semantic Validation (Permanent Solution to Noise & Whack-A-Mole)

A fundamental vulnerability of generic scrapers crawling government domains is that non-educational civic services (factory licenses, vehicle permits, agricultural grants, pilgrimage subsidies) share keywords like "scheme", "grant", or "yojana". Ad-hoc negative keyword blacklists create an endless "cat-and-mouse" game.

To solve this permanently, the engine enforces a **Positive Educational Aid Triple Invariant Contract** (`crawler/semantic_validator.py`):
1. **Pillar 1 (Program Identity)**: Must affirmatively define a discrete, named grant/fellowship program (e.g. *Post-Matric, Pragati, PMRF, INSPIRE SHE, Merit-cum-Means*). Generic portal roots, departmental gateways, and citizen service indexes are routed to `discovered_seeds` for link extraction and strictly blocked from entering the scholarships table.
2. **Pillar 2 (Academic Beneficiary)**: Must target enrolled students, scholars, or researchers pursuing recognized academic levels (*Class 9-12, Undergraduate, Postgraduate, Ph.D., Postdoc*).
3. **Pillar 3 (Educational Funding Purpose)**: Must explicitly fund educational tuition, academic stipends, research allowances, or study expenses.

**Zero-Score Barrier**: Any entity failing the contract is forced to $0.0\%$ confidence and stamped `REJECTED_NON_SCHOLARSHIP`. The SQLite persistence layer strictly refuses storage to any record failing this barrier.
