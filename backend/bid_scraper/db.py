"""
OmniTender MCP Bid Scraper - SQLite Storage & Persistence Layer.
Manages municipal solicitation records, documents, portal sync status,
full-text and faceted search queries for NC trade contractors.
"""

import os
import json
import sqlite3
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime, timezone

from backend.bid_scraper.models import (
    TenderItem,
    RFPDocument,
    MunicipalPortal,
    TenderSearchFilter,
    BidStatus,
    TradeCategory,
)
from backend.bid_scraper.portals import NC_MUNICIPAL_PORTALS

DEFAULT_DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")
DEFAULT_DB_PATH = os.path.join(DEFAULT_DB_DIR, "municipal_bids.db")


def get_db_path(custom_path: Optional[str] = None) -> str:
    """Resolves database file path, creating parent directory if necessary."""
    path = custom_path or os.environ.get("OMNITENDER_BIDS_DB_PATH") or DEFAULT_DB_PATH
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    return path


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Returns a SQLite connection with dict-like row factory and foreign keys enabled."""
    conn = sqlite3.connect(get_db_path(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: Optional[str] = None) -> None:
    """Initializes the database schema and seeds initial portal metadata."""
    conn = get_connection(db_path)
    try:
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS portals (
                    portal_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    jurisdiction TEXT NOT NULL,
                    county TEXT NOT NULL,
                    base_url TEXT NOT NULL,
                    portal_type TEXT NOT NULL,
                    active INTEGER DEFAULT 1,
                    last_scraped_at TEXT,
                    total_bids_found INTEGER DEFAULT 0,
                    notes TEXT
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS tenders (
                    id TEXT PRIMARY KEY,
                    portal_id TEXT NOT NULL,
                    jurisdiction TEXT NOT NULL,
                    county TEXT NOT NULL,
                    rfp_number TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    category TEXT NOT NULL,
                    trade TEXT NOT NULL,
                    issuing_agency TEXT NOT NULL,
                    estimated_budget REAL,
                    budget_currency TEXT DEFAULT 'USD',
                    posted_date TEXT,
                    closing_date TEXT,
                    status TEXT NOT NULL,
                    source_url TEXT NOT NULL,
                    contact_name TEXT,
                    contact_email TEXT,
                    contact_phone TEXT,
                    requirements_json TEXT,
                    pre_bid_meeting TEXT,
                    scraped_at TEXT NOT NULL,
                    raw_payload_json TEXT,
                    FOREIGN KEY (portal_id) REFERENCES portals (portal_id)
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS tender_documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tender_id TEXT NOT NULL,
                    doc_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    url TEXT NOT NULL,
                    doc_type TEXT DEFAULT 'specifications',
                    size_bytes INTEGER,
                    content_snippet TEXT,
                    FOREIGN KEY (tender_id) REFERENCES tenders (id) ON DELETE CASCADE
                )
            """)

            # Indexes for high performance filtering
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tenders_county ON tenders (county)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tenders_trade ON tenders (trade)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tenders_status ON tenders (status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tenders_closing ON tenders (closing_date)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tenders_portal ON tenders (portal_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_docs_tender ON tender_documents (tender_id)")

            # Seed default NC portals if not already present
            for portal in NC_MUNICIPAL_PORTALS.values():
                conn.execute("""
                    INSERT INTO portals (portal_id, name, jurisdiction, county, base_url, portal_type, active, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(portal_id) DO UPDATE SET
                        name = excluded.name,
                        jurisdiction = excluded.jurisdiction,
                        county = excluded.county,
                        base_url = excluded.base_url,
                        portal_type = excluded.portal_type,
                        notes = excluded.notes
                """, (
                    portal.portal_id,
                    portal.name,
                    portal.jurisdiction,
                    portal.county,
                    portal.base_url,
                    portal.portal_type,
                    1 if portal.active else 0,
                    portal.notes,
                ))
    finally:
        conn.close()


def upsert_tender(tender: TenderItem, db_path: Optional[str] = None) -> TenderItem:
    """Inserts or updates a tender and its associated documents."""
    conn = get_connection(db_path)
    try:
        with conn:
            conn.execute("""
                INSERT INTO tenders (
                    id, portal_id, jurisdiction, county, rfp_number, title, description,
                    category, trade, issuing_agency, estimated_budget, budget_currency,
                    posted_date, closing_date, status, source_url, contact_name,
                    contact_email, contact_phone, requirements_json, pre_bid_meeting,
                    scraped_at, raw_payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    portal_id = excluded.portal_id,
                    jurisdiction = excluded.jurisdiction,
                    county = excluded.county,
                    rfp_number = excluded.rfp_number,
                    title = excluded.title,
                    description = excluded.description,
                    category = excluded.category,
                    trade = excluded.trade,
                    issuing_agency = excluded.issuing_agency,
                    estimated_budget = excluded.estimated_budget,
                    budget_currency = excluded.budget_currency,
                    posted_date = excluded.posted_date,
                    closing_date = excluded.closing_date,
                    status = excluded.status,
                    source_url = excluded.source_url,
                    contact_name = excluded.contact_name,
                    contact_email = excluded.contact_email,
                    contact_phone = excluded.contact_phone,
                    requirements_json = excluded.requirements_json,
                    pre_bid_meeting = excluded.pre_bid_meeting,
                    scraped_at = excluded.scraped_at,
                    raw_payload_json = excluded.raw_payload_json
            """, (
                tender.id,
                tender.portal_id,
                tender.jurisdiction,
                tender.county,
                tender.rfp_number,
                tender.title,
                tender.description,
                tender.category,
                tender.trade.value if hasattr(tender.trade, 'value') else str(tender.trade),
                tender.issuing_agency,
                tender.estimated_budget,
                tender.budget_currency,
                tender.posted_date,
                tender.closing_date,
                tender.status.value if hasattr(tender.status, 'value') else str(tender.status),
                tender.source_url,
                tender.contact_name,
                tender.contact_email,
                tender.contact_phone,
                json.dumps(tender.requirements),
                tender.pre_bid_meeting,
                tender.scraped_at,
                json.dumps(tender.raw_payload) if tender.raw_payload else None,
            ))

            # Replace associated documents
            conn.execute("DELETE FROM tender_documents WHERE tender_id = ?", (tender.id,))
            for doc in tender.documents:
                conn.execute("""
                    INSERT INTO tender_documents (tender_id, doc_id, name, url, doc_type, size_bytes, content_snippet)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    tender.id,
                    doc.doc_id,
                    doc.name,
                    doc.url,
                    doc.doc_type,
                    doc.size_bytes,
                    doc.content_snippet,
                ))

            # Update portal last scraped & count
            conn.execute("""
                UPDATE portals
                SET last_scraped_at = ?,
                    total_bids_found = (SELECT COUNT(*) FROM tenders WHERE portal_id = ?)
                WHERE portal_id = ?
            """, (datetime.now(timezone.utc).isoformat(), tender.portal_id, tender.portal_id))
    finally:
        conn.close()
    return tender


def upsert_tenders(tenders: List[TenderItem], db_path: Optional[str] = None) -> int:
    """Batch upsert tenders."""
    count = 0
    for t in tenders:
        upsert_tender(t, db_path)
        count += 1
    return count


def _row_to_tender(row: sqlite3.Row, docs_rows: List[sqlite3.Row]) -> TenderItem:
    """Converts SQLite rows to a TenderItem Pydantic model."""
    docs = [
        RFPDocument(
            doc_id=d["doc_id"],
            name=d["name"],
            url=d["url"],
            doc_type=d["doc_type"] or "specifications",
            size_bytes=d["size_bytes"],
            content_snippet=d["content_snippet"],
        )
        for d in docs_rows
    ]

    reqs = []
    if row["requirements_json"]:
        try:
            reqs = json.loads(row["requirements_json"])
        except Exception:
            reqs = []

    raw = None
    if row["raw_payload_json"]:
        try:
            raw = json.loads(row["raw_payload_json"])
        except Exception:
            raw = None

    try:
        trade_enum = TradeCategory(row["trade"])
    except ValueError:
        trade_enum = TradeCategory.OTHER

    try:
        status_enum = BidStatus(row["status"])
    except ValueError:
        status_enum = BidStatus.OPEN

    return TenderItem(
        id=row["id"],
        portal_id=row["portal_id"],
        jurisdiction=row["jurisdiction"],
        county=row["county"],
        rfp_number=row["rfp_number"],
        title=row["title"],
        description=row["description"],
        category=row["category"],
        trade=trade_enum,
        issuing_agency=row["issuing_agency"],
        estimated_budget=row["estimated_budget"],
        budget_currency=row["budget_currency"] or "USD",
        posted_date=row["posted_date"],
        closing_date=row["closing_date"],
        status=status_enum,
        source_url=row["source_url"],
        contact_name=row["contact_name"],
        contact_email=row["contact_email"],
        contact_phone=row["contact_phone"],
        documents=docs,
        requirements=reqs,
        pre_bid_meeting=row["pre_bid_meeting"],
        scraped_at=row["scraped_at"],
        raw_payload=raw,
    )


def get_tender(tender_id: str, db_path: Optional[str] = None) -> Optional[TenderItem]:
    """Retrieves a single tender by its ID along with attached documents."""
    conn = get_connection(db_path)
    try:
        row = conn.execute("SELECT * FROM tenders WHERE id = ?", (tender_id,)).fetchone()
        if not row:
            return None
        docs = conn.execute("SELECT * FROM tender_documents WHERE tender_id = ?", (tender_id,)).fetchall()
        return _row_to_tender(row, docs)
    finally:
        conn.close()


def search_tenders(
    filter_params: TenderSearchFilter, db_path: Optional[str] = None
) -> Tuple[List[TenderItem], int]:
    """
    Searches and filters tenders by keyword query, county, trade, budget range, and status.
    Returns (results, total_count).
    """
    conn = get_connection(db_path)
    try:
        conditions = []
        params = []

        if filter_params.status:
            conditions.append("status = ?")
            params.append(filter_params.status.upper())

        if filter_params.county:
            conditions.append("LOWER(county) = LOWER(?)")
            params.append(filter_params.county.strip())

        if filter_params.trade:
            conditions.append("LOWER(trade) = LOWER(?)")
            params.append(filter_params.trade.strip())

        if filter_params.min_budget is not None and filter_params.min_budget > 0:
            conditions.append("estimated_budget >= ?")
            params.append(filter_params.min_budget)

        if filter_params.max_budget is not None and filter_params.max_budget > 0:
            conditions.append("estimated_budget <= ?")
            params.append(filter_params.max_budget)

        if filter_params.query:
            q = f"%{filter_params.query.strip()}%"
            conditions.append("(title LIKE ? OR description LIKE ? OR rfp_number LIKE ? OR category LIKE ?)")
            params.extend([q, q, q, q])

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        count_query = f"SELECT COUNT(*) as total FROM tenders {where_clause}"
        total = conn.execute(count_query, params).fetchone()["total"]

        data_query = f"""
            SELECT * FROM tenders
            {where_clause}
            ORDER BY closing_date ASC NULLS LAST, posted_date DESC
            LIMIT ? OFFSET ?
        """
        data_params = params + [filter_params.limit, filter_params.offset]
        rows = conn.execute(data_query, data_params).fetchall()

        results = []
        for r in rows:
            docs = conn.execute("SELECT * FROM tender_documents WHERE tender_id = ?", (r["id"],)).fetchall()
            results.append(_row_to_tender(r, docs))

        return results, total
    finally:
        conn.close()


def get_all_portals_from_db(db_path: Optional[str] = None) -> List[MunicipalPortal]:
    """Returns portal status and sync metrics from database."""
    conn = get_connection(db_path)
    try:
        rows = conn.execute("SELECT * FROM portals ORDER BY name ASC").fetchall()
        portals = []
        for r in rows:
            portals.append(
                MunicipalPortal(
                    portal_id=r["portal_id"],
                    name=r["name"],
                    jurisdiction=r["jurisdiction"],
                    county=r["county"],
                    base_url=r["base_url"],
                    portal_type=r["portal_type"],
                    active=bool(r["active"]),
                    last_scraped_at=r["last_scraped_at"],
                    total_bids_found=r["total_bids_found"] or 0,
                    notes=r["notes"],
                )
            )
        return portals
    finally:
        conn.close()


def get_stats(db_path: Optional[str] = None) -> Dict[str, Any]:
    """Returns aggregated summary metrics across the municipal database."""
    conn = get_connection(db_path)
    try:
        total_tenders = conn.execute("SELECT COUNT(*) FROM tenders").fetchone()[0]
        open_tenders = conn.execute("SELECT COUNT(*) FROM tenders WHERE status = 'OPEN'").fetchone()[0]
        total_budget = conn.execute("SELECT SUM(estimated_budget) FROM tenders WHERE status = 'OPEN'").fetchone()[0] or 0.0

        by_county = conn.execute("""
            SELECT county, COUNT(*) as count, SUM(estimated_budget) as total_val
            FROM tenders
            GROUP BY county
            ORDER BY count DESC
        """).fetchall()

        by_trade = conn.execute("""
            SELECT trade, COUNT(*) as count
            FROM tenders
            GROUP BY trade
            ORDER BY count DESC
        """).fetchall()

        return {
            "total_tenders": total_tenders,
            "open_tenders": open_tenders,
            "total_open_budget_est": round(total_budget, 2),
            "by_county": {row["county"]: {"count": row["count"], "total_val": row["total_val"] or 0.0} for row in by_county},
            "by_trade": {row["trade"]: row["count"] for row in by_trade},
        }
    finally:
        conn.close()
