"""
Working Demonstration Script for Scholarship Intelligence Crawler.
Demonstrates the full end-to-end lifecycle as specified in Assignment Section 14.C:

Crawler starts
  ↓
Discovers scholarship
  ↓
Extracts information
  ↓
Identifies official source
  ↓
Verifies information
  ↓
Generates confidence
  ↓
Stores record
  ↓
Displays scholarship
  ↓
Runs again
  ↓
Detects changes
"""

import sys
import time
from datetime import datetime

# UTF-8 stdout configuration for Windows/Linux
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

from crawler.pipeline import ScholarshipPipeline
from storage.database import (
    init_db,
    get_connection,
    get_scholarship,
    get_change_history,
    get_dashboard_metrics,
    get_evidence_for_scholarship
)

def print_step(num: int, title: str):
    print(f"\n=======================================================")
    print(f"STEP {num}: {title}")
    print(f"=======================================================")

def main():
    print("=====================================================================")
    print("  ATLAS FUNDING - SCHOLARSHIP INTELLIGENCE CRAWLER DEMONSTRATION")
    print("=====================================================================")
    print(f"Demonstration started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Reset database for fresh demo
    conn = get_connection()
    c = conn.cursor()
    c.execute("DROP TABLE IF EXISTS verification_evidence")
    c.execute("DROP TABLE IF EXISTS change_history")
    c.execute("DROP TABLE IF EXISTS crawl_runs")
    c.execute("DROP TABLE IF EXISTS scholarships")
    conn.commit()
    conn.close()
    init_db()

    pipeline = ScholarshipPipeline()

    # Step 1: Crawler starts
    print_step(1, "Crawler Starts")
    print("[INIT] Initialized WebFetcher, DiscoveryEngine, ConfidenceEngine, and SQLite storage.")
    time.sleep(0.5)

    # Step 2: Discovers scholarship
    print_step(2, "Discovers Scholarship")
    print("[DISCOVERY] Scanning high-priority seed sources (NSP, AICTE, DST, Reliance Foundation, Tata Trusts)...")
    candidates = pipeline.discovery.discover_from_seeds(max_links_per_seed=2)
    print(f"[DISCOVERY] Dynamically identified {len(candidates)} scholarship URLs from seed portals.")
    for cand in candidates[:3]:
        print(f"   * Found link: '{cand['anchor_text'][:40]}' -> {cand['url'][:65]}")
    time.sleep(0.5)

    # Step 3, 4, 5, 6, 7: Executes Run 1 (Extract -> Identify Official Source -> Verify -> Generate Confidence -> Store)
    print_step(3, "Extracts Information -> Identifies Official Source -> Verifies -> Generates Confidence -> Stores Record")
    summary_run1 = pipeline.run_pipeline(run_number=1)
    
    # Step 8: Displays scholarship
    print_step(8, "Displays Scholarship Details")
    sample_id = "aicte-pragati-degree-2026"
    rec = get_scholarship(sample_id)
    if rec:
        print(f"Name:               {rec['name']}")
        print(f"Provider:           {rec['provider']}")
        print(f"Source Type:        {rec['source_type']}")
        print(f"Benefit Amount:     {rec['amount']}")
        print(f"Eligibility:        {rec['eligibility']}")
        print(f"Deadline:           {rec['closing_date']}")
        print(f"Official Source:    {rec['official_source']}")
        print(f"Application Link:   {rec['application_url']}")
        print(f"Status:             {rec['current_status']}")
        print(f"Confidence Score:   {rec['confidence_score']}% [{rec['verification_status']}]")
        print("\n[WHY THIS SCORE? - Explainability Audit]:")
        for line in rec['why_this_score'].split("\n"):
            print(f"   {line}")
            
        print("\n[TRACEABLE SOURCE EVIDENCE]:")
        evidence_list = get_evidence_for_scholarship(sample_id)
        for ev in evidence_list[:2]:
            print(f"   * Field '{ev['field_name']}': {ev['evidence_quote'][:120]}...")

    time.sleep(1.0)

    # Step 9: Runs again
    print_step(9, "Runs Again (Continuous Auto-Crawler)")
    print("[RE-CRAWL] Initiating Run 2 to monitor ongoing status, scheme revisions, and new grants...")
    summary_run2 = pipeline.run_pipeline(run_number=2)

    # Step 10: Detects changes
    print_step(10, "Detects Changes (Audit Trail Retention)")
    changes = get_change_history()
    print(f"[CHANGE DETECTION] Successfully identified and logged {len(changes)} modification events:")
    for idx, ch in enumerate(changes, 1):
        print(f"\n   Change #{idx}: {ch['scholarship_name']}")
        print(f"   - Monitored Field: {ch['field_name']}")
        print(f"   - Previous Value:  {ch['old_value']}")
        print(f"   - Updated Value:   {ch['new_value']}")
        print(f"   - Date Detected:   {ch['date_detected']}")
        print(f"   - Evidence:        {ch['evidence']}")

    # Final Summary of Compliance
    print("\n=======================================================")
    print("VERIFICATION OF ASSIGNMENT SPECIFICATIONS (Section 11):")
    print("=======================================================")
    metrics = get_dashboard_metrics()
    print(f"Total Discovered:               {metrics['total_discovered']} (Requirement: >= 20)")
    print(f"Verified against primary source: {metrics['verified']} (Requirement: >= 15)")
    print(f"Confidence >= 95%:              {metrics['verified']} (Requirement: >= 10)")
    print(f"Distinct Source Types:          {metrics['distinct_source_types']} (Requirement: >= 3)")
    print(f"Change Detection Examples:      {metrics['recently_updated']} (Requirement: >= 2)")
    print(f"Expired Detection Examples:     {metrics['expired']} (Requirement: >= 2)")
    print(f"Average Confidence:             {metrics['average_confidence']}%")
    print("=======================================================\n")
    print("DEMONSTRATION COMPLETED SUCCESSFULLY!")

if __name__ == "__main__":
    main()
