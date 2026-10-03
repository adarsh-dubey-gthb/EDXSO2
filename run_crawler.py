"""
CLI Entry Point for Scholarship Intelligence Crawler.
Supports baseline discovery (Run 1) and continuous change detection (Run 2).
"""

import sys
import argparse
import time

# Ensure standard UTF-8 stream handling across all operating systems and terminals
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

from crawler.pipeline import ScholarshipPipeline
from storage.database import init_db, get_connection

def main():
    parser = argparse.ArgumentParser(description="Scholarship Intelligence Crawler Runner")
    parser.add_argument("--run", type=int, default=1, help="Crawl run iteration (1 = baseline, 2 = change detection)")
    parser.add_argument("--reset", action="store_true", help="Reset and clear database before running")
    parser.add_argument("--continuous", action="store_true", help="Run crawler continuously in background loop at scheduled interval")
    parser.add_argument("--interval", type=int, default=300, help="Interval in seconds between continuous crawl cycles (default: 300s)")
    parser.add_argument("--crawl-url", type=str, help="Crawl and ingest a custom live URL on-the-fly")
    parser.add_argument("--search", type=str, help="Search the open web dynamically to discover scholarship scheme links")
    args = parser.parse_args()

    if args.reset:
        print("Resetting database...")
        from storage.database import reset_db
        reset_db()
        print("Database initialized cleanly.")

    pipeline = ScholarshipPipeline()

    if args.crawl_url:
        print(f"\n>> Crawling custom URL: {args.crawl_url}")
        res = pipeline.crawl_and_ingest_url(args.crawl_url)
        if res["success"]:
            rec = res["record"]
            print(f"SUCCESS: Crawled & Ingested '{rec['name']}'")
            print(f"  * Provider:      {rec['provider']}")
            print(f"  * Status:        {rec['current_status']}")
            print(f"  * Verification:  {rec['verification_status']} ({rec['confidence_score']}%)")
            print(f"  * Amount:        {rec['amount']}")
            print(f"  * Deadline:      {rec['closing_date']}")
            print(f"  * Why Score:     {rec['why_this_score']}")
            if res["changes"]:
                print(f"  * Changes Detected: {len(res['changes'])}")
        else:
            print(f"FAILED: {res.get('error')}")
        return

    if args.search:
        print(f"\n>> Discovering open-web links for query: '{args.search}'")
        candidates = pipeline.discovery.discover_from_query(args.search, max_results=5)
        print(f"Found {len(candidates)} candidate portals:\n")
        for i, c in enumerate(candidates, 1):
            auth_str = "AUTHORITATIVE" if c["is_authoritative"] else "AGGREGATOR / SECONDARY"
            print(f"{i}. {c['title']}")
            print(f"   URL: {c['url']}")
            print(f"   Tier: {c['source_type']} [{auth_str}]")
            print(f"   Reason: {c['classification_reason']}")
            print()
        return

    if args.continuous:
        print(f"\n=======================================================")
        print(f">> STARTING CONTINUOUS AUTONOMOUS CRAWLER DAEMON")
        print(f">> Scheduled auto-crawl interval: {args.interval} seconds")
        print(f">> Auto-detects updates, new schemes & deadline extensions")
        print(f">> Press Ctrl+C to terminate.")
        print(f"=======================================================\n")
        cycle = 1
        while True:
            try:
                pipeline.run_pipeline(run_number=cycle)
                cycle += 1
                print(f"\n[DAEMON] Cycle complete. Sleeping for {args.interval}s until next auto-crawl cycle...")
                time.sleep(args.interval)
            except KeyboardInterrupt:
                print("\n[DAEMON] Continuous crawler stopped by user.")
                break
            except Exception as e:
                print(f"[DAEMON ERROR] Encountered error: {e}. Retrying in {args.interval}s...")
                time.sleep(args.interval)
        return

    pipeline.run_pipeline(run_number=args.run)

if __name__ == "__main__":
    main()
