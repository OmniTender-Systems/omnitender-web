"""
OmniTender MCP Bid Scraper - Automated Daily Cron Synchronization Service.
Executes scheduled recurring scans across North Carolina municipal portals,
updates the local SQLite solicitation database, and maintains synchronization logs.
"""

import os
import sys
import time
import json
import logging
import argparse
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional

_REPO_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from backend.bid_scraper.scrapers import AggregatorScraper
from backend.bid_scraper.db import get_stats, get_db_path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (CronSync) %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("omnitender.cron_sync")

DEFAULT_DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data"
)
LAST_SYNC_FILE = os.path.join(DEFAULT_DATA_DIR, "last_cron_sync.json")
SYNC_LOG_FILE = os.path.join(DEFAULT_DATA_DIR, "cron_sync.log")


def execute_cron_scan(
    use_playwright: bool = False,
    db_path: Optional[str] = None,
    output_receipt: bool = True,
) -> Dict[str, Any]:
    """
    Executes a complete scan cycle across all 5 NC municipal portals.
    Records duration, bids collected, errors, and updates receipt file.
    """
    os.makedirs(DEFAULT_DATA_DIR, exist_ok=True)
    start_time = time.time()
    iso_start = datetime.now(timezone.utc).isoformat()
    logger.info(f"Starting scheduled municipal RFP aggregation scan at {iso_start}...")

    aggregator = AggregatorScraper(db_path=db_path)
    result = aggregator.run_all(use_playwright=use_playwright)
    elapsed_sec = round(time.time() - start_time, 2)

    db_stats = get_stats(db_path=db_path)

    receipt: Dict[str, Any] = {
        "status": "SUCCESS",
        "started_at": iso_start,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "duration_seconds": elapsed_sec,
        "playwright_enabled": use_playwright,
        "portals_scanned": result.get("portals_scraped", 0),
        "total_bids_collected": result.get("total_bids_collected", 0),
        "total_bids_persisted": result.get("total_bids_persisted", 0),
        "portal_breakdown": result.get("portal_breakdown", {}),
        "database_totals": {
            "total_tenders": db_stats.get("total_tenders", 0),
            "open_tenders": db_stats.get("open_tenders", 0),
            "total_open_budget_est": db_stats.get("total_open_budget_est", 0.0),
        },
    }

    if output_receipt:
        try:
            with open(LAST_SYNC_FILE, "w", encoding="utf-8") as f:
                json.dump(receipt, f, indent=2)
            
            with open(SYNC_LOG_FILE, "a", encoding="utf-8") as log_f:
                log_entry = (
                    f"{receipt['completed_at']} | SUCCESS | "
                    f"duration={elapsed_sec}s | bids={receipt['total_bids_persisted']} | "
                    f"db_total={db_stats.get('total_tenders', 0)}\n"
                )
                log_f.write(log_entry)
        except Exception as file_err:
            logger.warning(f"Could not write cron receipt: {file_err}")

    logger.info(
        f"Scan complete in {elapsed_sec}s. "
        f"Persisted {receipt['total_bids_persisted']} bids across {receipt['portals_scanned']} NC portals."
    )
    return receipt


def run_daemon(interval_hours: float = 24.0, use_playwright: bool = False, db_path: Optional[str] = None):
    """Runs continuous background daemon executing scans every interval_hours."""
    logger.info(f"Starting OmniTender Bid Scraper Cron Daemon. Interval: {interval_hours} hours.")
    interval_seconds = max(60, int(interval_hours * 3600))

    while True:
        try:
            execute_cron_scan(use_playwright=use_playwright, db_path=db_path)
        except Exception as scan_err:
            logger.error(f"Error during scheduled cron scan: {scan_err}", exc_info=True)
        
        logger.info(f"Sleeping for {interval_hours}h ({interval_seconds}s) until next municipal scan...")
        time.sleep(interval_seconds)


def main():
    parser = argparse.ArgumentParser(description="OmniTender NC Municipal Bid Scraper Cron Runner")
    parser.add_argument("--once", action="store_true", help="Run a single scan cycle and exit.")
    parser.add_argument("--daemon", action="store_true", help="Run indefinitely as a scheduled daemon.")
    parser.add_argument(
        "--interval-hours",
        type=float,
        default=24.0,
        help="Hours between scans in daemon mode (default: 24.0).",
    )
    parser.add_argument(
        "--playwright",
        action="store_true",
        help="Attempt live Playwright headless browser navigation before fallback.",
    )
    parser.add_argument("--db", type=str, default=None, help="Custom SQLite DB path.")

    args = parser.parse_args()

    if args.daemon:
        run_daemon(interval_hours=args.interval_hours, use_playwright=args.playwright, db_path=args.db)
    else:
        receipt = execute_cron_scan(use_playwright=args.playwright, db_path=args.db)
        print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
