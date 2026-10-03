"""
SQLite database engine for the Scholarship Intelligence Crawler.
Provides persistent storage, schema enforcement, change tracking, and evidence auditing.
"""

import sqlite3
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from config.settings import DB_PATH
from storage.models import ScholarshipRecord, VerificationEvidence, ChangeLogEntry, CrawlRunSummary

def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def reset_db():
    """Clears and re-initializes all tables to establish clean baseline state."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS verification_evidence")
    cursor.execute("DROP TABLE IF EXISTS change_history")
    cursor.execute("DROP TABLE IF EXISTS crawl_runs")
    cursor.execute("DROP TABLE IF EXISTS scholarships")
    cursor.execute("DROP TABLE IF EXISTS discovered_seeds")
    conn.commit()
    conn.close()
    init_db()

def init_db():
    """Initializes tables for scholarships, verification evidence, change history, and crawl runs."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Main Scholarships Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS scholarships (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        provider TEXT NOT NULL,
        official_source TEXT NOT NULL,
        application_url TEXT,
        source_type TEXT NOT NULL,
        amount TEXT,
        eligibility TEXT,
        academic_requirements TEXT,
        course_level TEXT,
        income_criteria TEXT,
        age_criteria TEXT,
        gender_criteria TEXT,
        category_criteria TEXT,
        domicile_requirements TEXT,
        institution_requirements TEXT,
        opening_date TEXT,
        closing_date TEXT,
        documents_required TEXT,
        selection_process TEXT,
        renewal_requirements TEXT,
        current_status TEXT NOT NULL,
        confidence_score REAL NOT NULL,
        verification_status TEXT NOT NULL,
        date_last_verified TEXT NOT NULL,
        why_this_score TEXT,
        source_evidence TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    # 2. Verification Evidence Table (Fine-grained field-level traceability)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS verification_evidence (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        scholarship_id TEXT NOT NULL,
        field_name TEXT NOT NULL,
        evidence_quote TEXT NOT NULL,
        source_url TEXT NOT NULL,
        verified_at TEXT NOT NULL,
        FOREIGN KEY (scholarship_id) REFERENCES scholarships(id) ON DELETE CASCADE
    );
    """)
    
    # 3. Change History Table (Section 7: Change Detection retention)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS change_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        scholarship_id TEXT NOT NULL,
        field_name TEXT NOT NULL,
        old_value TEXT,
        new_value TEXT,
        date_detected TEXT NOT NULL,
        source TEXT NOT NULL,
        evidence TEXT NOT NULL,
        FOREIGN KEY (scholarship_id) REFERENCES scholarships(id) ON DELETE CASCADE
    );
    """)
    
    # 4. Crawl Runs Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS crawl_runs (
        run_id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        total_discovered INTEGER,
        verified_count INTEGER,
        review_required_count INTEGER,
        active_count INTEGER,
        expired_count INTEGER,
        changes_detected_count INTEGER,
        avg_confidence REAL,
        notes TEXT
    );
    """)

    # 5. Discovered Seeds Table — Persistent Frontier Expansion
    # When the crawler finds a new authoritative external domain that is NOT in the
    # hardcoded seed list, it is saved here. Every future crawl loads these as
    # additional seeds so the crawler's universe grows automatically over time.
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS discovered_seeds (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        url TEXT NOT NULL UNIQUE,
        domain TEXT NOT NULL,
        name TEXT,
        source_type TEXT DEFAULT 'Central Government',
        is_authoritative INTEGER DEFAULT 0,
        discovery_source TEXT,
        first_discovered TEXT NOT NULL,
        last_crawled TEXT,
        times_crawled INTEGER DEFAULT 0,
        avg_confidence REAL DEFAULT 0.0,
        is_active INTEGER DEFAULT 1
    );
    """)

    conn.commit()
    conn.close()


def save_discovered_seed(url: str, domain: str, name: str = "", source_type: str = "Central Government",
                          is_authoritative: bool = False, discovery_source: str = ""):
    """
    Persistently saves a newly discovered external domain/URL as a future crawl seed.
    Idempotent — calling it twice with the same URL is safe (UPSERT).
    """
    conn = get_connection()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("""
        INSERT INTO discovered_seeds (url, domain, name, source_type, is_authoritative, discovery_source, first_discovered)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(url) DO UPDATE SET
            name = COALESCE(NULLIF(excluded.name, ''), discovered_seeds.name),
            is_authoritative = MAX(discovered_seeds.is_authoritative, excluded.is_authoritative),
            is_active = 1
    """, (url, domain, name, source_type, int(is_authoritative), discovery_source, now))
    conn.commit()
    conn.close()


def load_discovered_seeds() -> List[Dict[str, Any]]:
    """
    Loads all active previously-discovered external seeds from the DB.
    These are added to the crawl frontier alongside the hardcoded SEED_SOURCES
    so the crawler expands its coverage automatically over time.
    """
    conn = get_connection()
    rows = conn.execute("""
        SELECT url, domain, name, source_type, is_authoritative, 
               discovery_source, first_discovered, last_crawled, times_crawled, avg_confidence
        FROM discovered_seeds
        WHERE is_active = 1
        ORDER BY id DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_seed_crawled(url: str, avg_confidence: float = 0.0):
    """Updates crawl statistics for a discovered seed after it has been processed."""
    conn = get_connection()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("""
        UPDATE discovered_seeds
        SET last_crawled = ?, times_crawled = times_crawled + 1, avg_confidence = ?
        WHERE url = ?
    """, (now, avg_confidence, url))
    conn.commit()
    conn.close()

def save_or_update_scholarship(
    record: ScholarshipRecord, 
    evidence_list: Optional[List[VerificationEvidence]] = None,
    track_changes: bool = True
) -> Tuple[bool, List[ChangeLogEntry]]:
    """
    Saves a scholarship. If already present, detects changes on critical fields,
    logs the change history without silently overwriting, and updates the record.
    Returns (is_new, changes_detected_list).
    """
    # Storage-layer invariant barrier: Never persist rejected non-scholarship entities
    if record.verification_status == "REJECTED_NON_SCHOLARSHIP" or record.confidence_score <= 0.0:
        return False, []

    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM scholarships WHERE id = ?", (record.id,))
    existing = cursor.fetchone()

    
    changes: List[ChangeLogEntry] = []
    now_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if existing is not None:
        is_new = False
        if track_changes:
            # Fields monitored for change detection
            monitored_fields = [
                ("closing_date", "Deadline"),
                ("amount", "Benefit Amount"),
                ("current_status", "Current Status"),
                ("eligibility", "Eligibility Criteria"),
                ("application_url", "Application URL"),
                ("income_criteria", "Income Limit")
            ]
            
            for field_key, field_label in monitored_fields:
                old_val = str(existing[field_key]) if existing[field_key] is not None else ""
                new_val = str(getattr(record, field_key)) if getattr(record, field_key) is not None else ""
                
                # Check for meaningful change
                if old_val.strip() != new_val.strip() and old_val.strip() != "":
                    entry = ChangeLogEntry(
                        scholarship_id=record.id,
                        field_name=field_label,
                        old_value=old_val,
                        new_value=new_val,
                        date_detected=now_iso,
                        source=record.official_source,
                        evidence=f"Updated during crawler sync: {field_label} modified from '{old_val}' to '{new_val}' as verified from {record.official_source}"
                    )
                    changes.append(entry)
                    
                    cursor.execute("""
                        INSERT INTO change_history (scholarship_id, field_name, old_value, new_value, date_detected, source, evidence)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (entry.scholarship_id, entry.field_name, entry.old_value, entry.new_value, entry.date_detected, entry.source, entry.evidence))
                    
        # Update scholarship record
        cursor.execute("""
            UPDATE scholarships SET
                name = ?, provider = ?, official_source = ?, application_url = ?, source_type = ?,
                amount = ?, eligibility = ?, academic_requirements = ?, course_level = ?,
                income_criteria = ?, age_criteria = ?, gender_criteria = ?, category_criteria = ?,
                domicile_requirements = ?, institution_requirements = ?, opening_date = ?,
                closing_date = ?, documents_required = ?, selection_process = ?,
                renewal_requirements = ?, current_status = ?, confidence_score = ?,
                verification_status = ?, date_last_verified = ?, why_this_score = ?,
                source_evidence = ?, updated_at = ?
            WHERE id = ?
        """, (
            record.name, record.provider, record.official_source, record.application_url, record.source_type,
            record.amount, record.eligibility, record.academic_requirements, record.course_level,
            record.income_criteria, record.age_criteria, record.gender_criteria, record.category_criteria,
            record.domicile_requirements, record.institution_requirements, record.opening_date,
            record.closing_date, record.documents_required, record.selection_process,
            record.renewal_requirements, record.current_status, record.confidence_score,
            record.verification_status, record.date_last_verified, record.why_this_score,
            record.source_evidence, now_iso, record.id
        ))
    else:
        is_new = True
        cursor.execute("""
            INSERT INTO scholarships (
                id, name, provider, official_source, application_url, source_type,
                amount, eligibility, academic_requirements, course_level,
                income_criteria, age_criteria, gender_criteria, category_criteria,
                domicile_requirements, institution_requirements, opening_date,
                closing_date, documents_required, selection_process,
                renewal_requirements, current_status, confidence_score,
                verification_status, date_last_verified, why_this_score,
                source_evidence, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record.id, record.name, record.provider, record.official_source, record.application_url, record.source_type,
            record.amount, record.eligibility, record.academic_requirements, record.course_level,
            record.income_criteria, record.age_criteria, record.gender_criteria, record.category_criteria,
            record.domicile_requirements, record.institution_requirements, record.opening_date,
            record.closing_date, record.documents_required, record.selection_process,
            record.renewal_requirements, record.current_status, record.confidence_score,
            record.verification_status, record.date_last_verified, record.why_this_score,
            record.source_evidence, now_iso, now_iso
        ))
        
    # Store fine-grained evidence snippets
    if evidence_list:
        # Clear previous evidence for fresh overwrite
        cursor.execute("DELETE FROM verification_evidence WHERE scholarship_id = ?", (record.id,))
        for ev in evidence_list:
            cursor.execute("""
                INSERT INTO verification_evidence (scholarship_id, field_name, evidence_quote, source_url, verified_at)
                VALUES (?, ?, ?, ?, ?)
            """, (ev.scholarship_id, ev.field_name, ev.evidence_quote, ev.source_url, ev.verified_at))
            
    conn.commit()
    conn.close()
    return is_new, changes

def get_scholarship(scholarship_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM scholarships WHERE id = ?", (scholarship_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def list_scholarships(
    query: Optional[str] = None,
    status: Optional[str] = None,
    source_type: Optional[str] = None,
    min_confidence: Optional[float] = None
) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    sql = "SELECT * FROM scholarships WHERE 1=1"
    params = []
    
    if query:
        sql += " AND (name LIKE ? OR provider LIKE ? OR eligibility LIKE ?)"
        pattern = f"%{query}%"
        params.extend([pattern, pattern, pattern])
        
    if status and status != "ALL":
        sql += " AND current_status = ?"
        params.append(status)
        
    if source_type and source_type != "ALL":
        sql += " AND source_type = ?"
        params.append(source_type)
        
    if min_confidence is not None:
        sql += " AND confidence_score >= ?"
        params.append(min_confidence)
        
    sql += " ORDER BY confidence_score DESC, name ASC"
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_change_history(scholarship_id: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    if scholarship_id:
        cursor.execute("""
            SELECT ch.*, s.name as scholarship_name 
            FROM change_history ch
            JOIN scholarships s ON ch.scholarship_id = s.id
            WHERE ch.scholarship_id = ?
            ORDER BY ch.id DESC
        """, (scholarship_id,))
    else:
        cursor.execute("""
            SELECT ch.*, s.name as scholarship_name 
            FROM change_history ch
            JOIN scholarships s ON ch.scholarship_id = s.id
            ORDER BY ch.id DESC
        """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_evidence_for_scholarship(scholarship_id: str) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM verification_evidence
        WHERE scholarship_id = ?
        ORDER BY id ASC
    """, (scholarship_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_dashboard_metrics() -> Dict[str, Any]:
    """Calculates all aggregate metrics requested in Section 10 of assignment."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM scholarships")
    total = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT COUNT(*) FROM scholarships WHERE verification_status = 'VERIFIED'")
    verified = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT COUNT(*) FROM scholarships WHERE verification_status = 'REVIEW_REQUIRED'")
    review_required = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT COUNT(*) FROM scholarships WHERE current_status = 'ACTIVE'")
    active = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT COUNT(*) FROM scholarships WHERE current_status = 'EXPIRED'")
    expired = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT COUNT(*) FROM change_history")
    changes_detected = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT AVG(confidence_score) FROM scholarships")
    avg_conf = cursor.fetchone()[0] or 0.0
    
    cursor.execute("SELECT COUNT(DISTINCT source_type) FROM scholarships")
    distinct_source_types = cursor.fetchone()[0] or 0
    
    conn.close()
    
    return {
        "total_discovered": total,
        "verified": verified,
        "review_required": review_required,
        "active": active,
        "expired": expired,
        "recently_updated": changes_detected,
        "average_confidence": round(avg_conf, 1),
        "distinct_source_types": distinct_source_types
    }

def record_crawl_run(summary: CrawlRunSummary):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO crawl_runs (
            timestamp, total_discovered, verified_count, review_required_count,
            active_count, expired_count, changes_detected_count, avg_confidence, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        summary.timestamp, summary.total_discovered, summary.verified_count,
        summary.review_required_count, summary.active_count, summary.expired_count,
        summary.changes_detected_count, summary.avg_confidence,
        f"Completed run with {summary.changes_detected_count} changes detected"
    ))
    conn.commit()
    conn.close()
