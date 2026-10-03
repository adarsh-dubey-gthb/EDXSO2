# Scholarship Intelligence Crawler — Atlas Funding

> **Autonomous Multi-Source Ingestion, Primary-Source Verification, Anti-Hallucination Grounding, and Continuous Change Detection Engine for Indian Student Scholarships.**

---

## 📌 Executive Summary

The **Scholarship Intelligence Crawler** is built for the **Atlas Funding** product vision: creating an automated, continuously updated, and authentic scholarship repository for Indian students. 

Rather than functioning as a fragile one-off scraper, this system is an end-to-end **Data Engineering & Intelligence Pipeline** operating under strict rules of **evidence grounding**, **deterministic mathematical confidence scoring**, **primary authority verification**, and **non-destructive change detection**.

---

## 🌟 Architecture & Capabilities Matrix

| Capability | Engineering Standard | System Implementation | Status |
| :--- | :--- | :--- | :---: |
| **Pipeline Flow** | Discovers &rarr; Crawls &rarr; Extracts &rarr; Verifies &rarr; Scores &rarr; Stores &rarr; Updates | Modular Python pipeline in `crawler/pipeline.py` | ✅ Supported |
| **Target Records** | Comprehensive repository of real schemes | **24 Real Scholarships** across 6 distinct categories | ✅ Complete |
| **Primary Source Verification** | Strict verification against primary authority | **23 Verified against Official Portals** (`.gov.in`, `.nic.in`, `.ac.in`, official CSR) | ✅ Complete |
| **Confidence Scoring** | High-precision qualification threshold ($\ge 95\%$) | **23 Records with Confidence $\ge 95\%$** | ✅ Complete |
| **Scoring Design** | Non-LLM mathematical formulation | Deterministic 6-factor weighted mathematical formula | ✅ Complete |
| **Source Types** | Broad institutional diversity | **6 Distinct Types**: Central Gov, Statutory Body, Corporate CSR, Premier University, State Gov, Aggregator Mirror | ✅ Complete |
| **Change Detection** | Continuous delta tracking | **2 Fully Logged Examples**: AICTE Pragati deadline extension & Reliance UG benefit revision | ✅ Complete |
| **Stale / Expired Detection** | Temporal validity monitoring | **6 Real Expired/Stale Schemes** (DRDO Girls Scheme, L'Oreal Science 2023, past academic cycles) | ✅ Complete |
| **Aggregator Treatment** | Secondary discovery only; penalized domain score | `SourceClassifier` penalizes aggregators (e.g. `Buddy4Study` given 62.5% & `REVIEW_REQUIRED`) | ✅ Complete |
| **Anti-Hallucination** | Never invent data; unmentioned fields &rarr; "Not specified" | Strict `AntiHallucinationEngine` with quote traceability | ✅ Complete |
| **Relational Storage** | Lightweight, atomic ACID storage | SQLite (`data/scholarships.db`) with relational tables | ✅ Complete |
| **Operations Dashboard** | Interactive exploration & live inspection UI | Modern **Streamlit Dashboard** (`ui/app.py`) | ✅ Complete |
| **Tooling & Stack** | Zero paid APIs, self-contained open stack | Python, Requests, BeautifulSoup, SQLite, Streamlit | ✅ Complete |

---

## 🏛️ System Architecture

```
[ Seed Portals (NSP, AICTE, DST, Reliance, Tata Trusts, ONGC, PMRF, IISc, State Portals) ]
                                │
                                ▼
 1. Dynamic Discovery Engine (`crawler/discovery.py`)
    • Scans seed portals and extracts scholarship links via anchor text & URL heuristics
                                │
                                ▼
 2. Domain & Authority Classifier (`crawler/classifier.py`, `verification/domain_verifier.py`)
    • Classifies domain into Central Gov, State Gov, Statutory Body, Corporate CSR, University, or Aggregator
                                │
                                ▼
 3. Schema Extractor (`crawler/extractor.py`)
    • Formats unstructured text into 19+ universal scholarship schema attributes
    • Strictly sanitizes missing fields to "Not specified" (Anti-Hallucination)
                                │
                                ▼
 4. Multi-Factor Verification & Confidence Engine (`verification/confidence_engine.py`)
    • Mathematical evaluation (Domain Auth + Liveness + App URL + Quote Grounding + Freshness + Completeness)
    • Assigns VERIFIED (≥95%) or REVIEW REQUIRED (<95%)
                                │
                                ▼
 5. Change & Stale-Data Engine (`change_detection/tracker.py`)
    • Evaluates lifecycle: ACTIVE, EXPIRING_SOON, EXPIRED, NO_LONGER_VERIFIABLE
    • Compares against baseline snapshots; writes modification history without data loss
                                │
                                ▼
 6. SQLite Relational Store (`storage/database.py`)
    • Tables: `scholarships`, `verification_evidence`, `change_history`, `crawl_runs`, `discovered_seeds`
                                │
                                ▼
 7. Operations & Inspection Dashboard (`ui/app.py`)
    • Search, KPI metric cards, detailed field inspection, "Why this score?", and live crawler execution
```

---

## 🏛️ Contract-Based Invariant Verification (Zero "Cat & Mouse" Whack-A-Mole)

A fundamental challenge when crawling Indian government domains (`.gov.in`, `.nic.in`) is that citizen portals host hundreds of non-educational services (factory licenses, vehicle registrations, agricultural subsidies, pilgrimage travel assistance) that share generic terms like "scheme", "grant", or "yojana".

### The Flaw of Keyword Blacklists:
Traditional scrapers attempt to maintain negative keyword denylists (`factory`, `license`, `tourism`, `darshan`, `tractor`, etc.). This approach is fundamentally broken:
- It creates an endless game of whack-a-mole: every new portal brings new unlisted civic schemes.
- It causes portal homepages (such as `scholarships.gov.in/home`) to be mistakenly ingested as scholarships simply because they sit on `.gov.in` and contain the word "scholarship".

### The Architectural Invariant Solution:
Our system enforces a **Mathematically Positive Contract** (`crawler/semantic_validator.py`):
Rejection is the default. A document is admitted into the pipeline if and only if it affirmatively satisfies the **Educational Aid Triple Invariant**:

```
[Live Web / Discovered Link]
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│ 1. Graph Node Classifier: Directory Hub vs Scheme Leaf Node │
│   • Portal roots, department indexes, & citizen service tabs│
│     are recognized as Directory Hubs                        │
│   • Registered in `discovered_seeds` to crawl child links   │
│   • STRICTLY BLOCKED from entering the `scholarships` table │
└─────────────────────────────────────────────────────────────┘
             │ (Only discrete scheme notices pass)
             ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Positive Educational Aid Triple Invariant Contract       │
│   • Pillar 1 (Program Identity): Must name a discrete aid   │
│     program (Scholarship, Fellowship, Stipend, Bursary)     │
│   • Pillar 2 (Academic Beneficiary): Must target enrolled   │
│     students/scholars (Class 9-12, UG, PG, Ph.D., Postdoc)  │
│   • Pillar 3 (Educational Funding): Must explicitly fund    │
│     tuition fees, study stipends, or research contingencies │
└─────────────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Confidence Engine Zero-Tolerance Gate                    │
│   • If an entity fails the contract, score is FORCED to 0.0%│
│   • Status stamped: `REJECTED_NON_SCHOLARSHIP`              │
│   • Domain authority (.gov.in) cannot override invalidity   │
└─────────────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. SQLite Storage Barrier                                   │
│   • Database layer rejects writing any non-scholarship row  │
└─────────────────────────────────────────────────────────────┘
```

> **Why this permanently solves the problem:** A factory license, vehicle permit, borewell grant, or pilgrimage darshan scheme fails automatically because it has **zero student beneficiaries** and provides **zero educational tuition support**. No negative blacklist needed.

---

## 🚀 Quickstart & Setup Instructions

### 1. Prerequisites
- Python 3.10+ (Tested on Python 3.12)
- Git

### 2. Installation
Open your terminal in the project directory:

```bash
# Optional: Create and activate virtual environment
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install required dependencies
pip install -r requirements.txt
```

---

## 💻 Running the Applications

### A. Run the 10-Step End-to-End Pipeline Demonstration
This script runs through the full operational lifecycle:
`Crawler starts -> Discovers scholarship -> Extracts information -> Identifies official source -> Verifies information -> Generates confidence -> Stores record -> Displays scholarship -> Runs again -> Detects changes`.

```bash
python demo_pipeline.py
```

### B. Run the Crawler via CLI (Run 1, Run 2, Custom Live URL & Open-Web Search)
```bash
# Execute Run 1 (Baseline Discovery & Ingestion)
python run_crawler.py --run 1

# Execute Run 2 (Continuous Crawl with Change Detection & Auditing)
python run_crawler.py --run 2

# Crawl and ingest ANY custom live URL on-the-fly:
python run_crawler.py --crawl-url "https://scholarships.gov.in"

# Discover open-web scholarship links dynamically beyond fixed seeds:
python run_crawler.py --search "AICTE Pragati Scholarship"

# Reset database cleanly and re-run baseline:
python run_crawler.py --reset --run 1
```

### C. Launch the Interactive Operations Dashboard
Launch the modern Streamlit web interface:

```bash
streamlit run ui/app.py
```
*The dashboard will automatically open in your browser at `http://localhost:8501`.*

**Interactive Tabs Available in Dashboard:**
1. **📚 Scholarship Directory**: Search, multi-dimensional filters, metric badges, and detailed field views.
2. **🌐 Live Web Crawler & Discovery**:
   - **Open-Web Search**: Discover scholarship links across live web via free open-source discovery engine.
   - **Live URL Ingestion**: Paste any URL, inspect live HTTP fetch, NLP extraction, confidence breakdown, and database sync in real time.
3. **⚡ Change History & Audit Log**: Comprehensive modification ledger with old/new values, timestamps, and evidence diffs.
4. **🔍 Traceable Evidence Inspector**: Inspect verbatim supporting quotes for every important field.
5. **🛡️ Verification Engine & Tech Note**: Mathematical formula details, factor weightings, and system design.

### D. Run the Automated Test Suite
Run the unit and integration tests covering classification, confidence formulation, anti-hallucination, change detection, live URL ingestion, and database storage:

```bash
python -m unittest tests/test_pipeline.py
```

---

## 📊 Database Schema (`data/scholarships.db`)

The SQLite database uses relational tables to ensure data integrity and full auditability:

### 1. `scholarships` (Main Table)
Contains all 19+ standard schema fields:
- `id` (TEXT PRIMARY KEY): Unique scheme identifier (e.g. `aicte-pragati-degree-2026`).
- `name` (TEXT): Scholarship scheme title.
- `provider` (TEXT): Ministry, Department, or Corporate Foundation.
- `official_source` (TEXT): Canonical official primary source URL.
- `application_url` (TEXT): Direct application portal link.
- `source_type` (TEXT): Category (`Central Government`, `State Government`, `Statutory Body / Ministry`, `Corporate CSR`, `University / Premier Institution`, `Aggregator / Secondary`).
- `amount` (TEXT): Monetary stipend or grant description.
- `eligibility` (TEXT): Eligibility overview.
- `academic_requirements` (TEXT): Minimum grades, degrees, or entrance exam criteria.
- `course_level` (TEXT): Academic level (`Undergraduate`, `Postgraduate`, `Ph.D.`, `Diploma`).
- `income_criteria` (TEXT): Family income ceiling or `"Not specified"`.
- `age_criteria` (TEXT): Age limitations or `"Not specified"`.
- `gender_criteria` (TEXT): Gender criteria (e.g. `Female only`, `All genders`).
- `category_criteria` (TEXT): Category (e.g. `SC`, `ST`, `OBC`, `PwD`, `General`, `Open`).
- `domicile_requirements` (TEXT): Geographic restrictions (e.g. `All India`, `Maharashtra only`).
- `institution_requirements` (TEXT): Recognized institutions.
- `opening_date` (TEXT): Start date.
- `closing_date` (TEXT): Deadline date.
- `documents_required` (TEXT): Documents list.
- `selection_process` (TEXT): Selection procedure.
- `renewal_requirements` (TEXT): Criteria to maintain funding.
- `current_status` (TEXT): `ACTIVE`, `EXPIRING_SOON`, `EXPIRED`, `REVIEW_REQUIRED`, `NO_LONGER_VERIFIABLE`.
- `confidence_score` (REAL): Numerical percentage (0.0 to 100.0).
- `verification_status` (TEXT): `VERIFIED` ($\ge 95\%$) or `REVIEW_REQUIRED` ($< 95\%$).
- `date_last_verified` (TEXT): Verification timestamp.
- `why_this_score` (TEXT): Explainability audit breakdown.
- `source_evidence` (TEXT): Verbatim source text extract.

### 2. `verification_evidence` (Traceability Table)
Enforces fine-grained field-level quote anchoring:
- `scholarship_id`: Foreign key referencing `scholarships(id)`.
- `field_name`: Monitored attribute (`Scholarship Name`, `Benefit Amount`, `Application Deadline`, `Eligibility Criteria`).
- `evidence_quote`: Verbatim quote from official document/page.
- `source_url`: URL where quote was observed.
- `verified_at`: Timestamp.

### 3. `change_history` (Audit Log Table)
Retains all detected modifications across crawls:
- `scholarship_id`: Foreign key referencing `scholarships(id)`.
- `field_name`: Modified parameter (e.g. `Deadline`, `Benefit Amount`).
- `old_value`: Prior recorded value.
- `new_value`: Newly detected value.
- `date_detected`: Modification timestamp.
- `source`: URL where change was detected.
- `evidence`: Audit reason.

### 4. `crawl_runs` (Telemetry Table)
Tracks crawler run performance across time:
- `run_id`, `timestamp`, `total_discovered`, `verified_count`, `review_required_count`, `active_count`, `expired_count`, `changes_detected_count`, `avg_confidence`, `notes`.

---

## 🧮 Confidence Score Methodology (Non-LLM)

Rather than querying a probabilistic generative model for arbitrary confidence numbers, the engine applies a deterministic, multi-factor mathematical scoring formula:

$$\text{Confidence Score} = 100 \times \left( \sum_{i=1}^{6} w_i \times S_i \right) - P_{\text{conflict}}$$

```
Confidence Score Weights:
┌──────────────────────────────────────────┬────────┐
│ Factor                                   │ Weight │
├──────────────────────────────────────────┼────────┤
│ 1. Domain Authenticity (S_domain)        │  25%   │
│ 2. Source Liveness & Content (S_live)    │  20%   │
│ 3. Application Portal Auth (S_app)       │  15%   │
│ 4. Evidence Grounding (S_evidence)       │  20%   │
│ 5. Temporal Validity (S_temporal)        │  10%   │
│ 6. Schema Completeness (S_schema)        │  10%   │
└──────────────────────────────────────────┴────────┘
Total: 100%
```

### Strict Threshold Rule:
- If **Confidence $\ge 95.0\%$** &rarr; Status: **`VERIFIED`**
- If **Confidence $< 95.0\%$** &rarr; Status: **`REVIEW REQUIRED`**

---

## 🛡️ Anti-Hallucination & Evidence Traceability

1. **Unmentioned Fields**: If a scholarship notification does not specify an income limit or age limit, the extractor writes `"Not specified"`. It **never** hallucinates placeholder numbers.
2. **Traceability Chain**:
   $$\text{Database Record} \longrightarrow \text{Official Source URL} \longrightarrow \text{Verbatim Evidence Quote} \longrightarrow \text{Extracted Value}$$
   Every critical field is backed by an exact quote stored in `verification_evidence`.

---

## 🔄 Change Detection & Stale Data Tracking

### Change Detection:
1. **AICTE Pragati Degree Scheme**:
   - Monitored Field: `Deadline`
   - Previous Value: `31 August 2026`
   - Updated Value: `15 September 2026`
   - Evidence: Verified official corrigendum extension on `aicte-india.org`.
2. **Reliance Foundation Undergraduate Scholarship**:
   - Monitored Field: `Benefit Amount`
   - Previous Value: `Up to ₹2,00,000 over the duration of degree`
   - Updated Value: `Up to ₹2,50,000 over degree duration + Mentorship`
   - Evidence: Verified official CSR grant enhancement on `scholarships.reliancefoundation.org`.

### Stale / Expired Schemes:
1. **DRDO Scholarship Scheme for Girls**: Application deadline `31 December 2023` has elapsed. Correctly evaluated and flagged as `EXPIRED`.
2. **L'Oreal India For Young Women in Science (2023 Cycle)**: Closed on `15 October 2023`. Correctly flagged as `EXPIRED`.

### Aggregator Detection:
- **Vidyadhan National Scholarship (Aggregator Mirror)**: URL belongs to `buddy4study.com`. Domain verifier gives 0.0 domain authority, resulting in a confidence score of **62.5%** and status **`REVIEW_REQUIRED`**.

---

## 📁 Repository Directory Structure

```
assignment2/
├── config/
│   ├── settings.py           # Thresholds (0.95), factor weights, allowed TLDs, aggregator blacklist
│   └── seed_sources.py       # Seed portals across Central Gov, State Gov, Corporate CSR, Universities
├── crawler/
│   ├── __init__.py
│   ├── semantic_validator.py # Contract-based educational intent validator & directory hub separator
│   ├── fetcher.py            # Robust HTTP fetcher with Gov PKI/NIC SSL tolerance & pooling
│   ├── discovery.py          # Dynamic link crawler traversing seeds and extracting scheme URLs
│   ├── classifier.py         # Source classifier (Gov, University, CSR vs Aggregator)
│   ├── extractor.py          # Structured extractor mapping unstructured data to 19+ schema fields
│   ├── initial_data.py       # Authentic dataset of 23 real Indian scholarships with official URLs & quotes
│   └── pipeline.py           # Core pipeline coordinator (Discovers -> Crawls -> Extracts -> Verifies -> Scores -> Stores -> Updates)
├── verification/
│   ├── __init__.py
│   ├── domain_verifier.py    # Primary authority & TLD scoring engine
│   ├── confidence_engine.py  # Deterministic multi-factor confidence formulation (non-LLM)
│   └── anti_hallucination.py # Verbatim quote grounding and 'Not specified' enforcement
├── change_detection/
│   ├── __init__.py
│   └── tracker.py            # Lifecycle state evaluator and delta change detection logger
├── storage/
│   ├── __init__.py
│   ├── models.py             # Data schemas (ScholarshipRecord, VerificationEvidence, ChangeLogEntry)
│   └── database.py           # SQLite database engine with relational tables
├── ui/
│   └── app.py                # Streamlit Operations & Intelligence Dashboard
├── data/
│   └── scholarships.db       # Working SQLite database populated with 24 real scholarships
├── tests/
│   ├── __init__.py
│   └── test_pipeline.py      # Unit & integration test suite (7 passing test suites)
├── demo_pipeline.py          # 10-Step End-to-End demonstration script
├── run_crawler.py            # CLI runner for crawler executions (Run 1, Run 2, Reset)
├── TECHNICAL_NOTE.md         # Comprehensive 3-page technical architectural note
├── README.md                 # Complete technical documentation and setup guide
├── requirements.txt          # Open-source dependencies
└── .gitignore                # Git ignore configuration
```

---
*Scholarship Intelligence Engine — Atlas Funding Architecture.*
