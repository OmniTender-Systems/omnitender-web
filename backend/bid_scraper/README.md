# OmniTender MCP Bid Scraper: Autonomous Municipal RFP Aggregation Engine

A production-grade pipeline component and FastMCP server for autonomous North Carolina municipal RFP aggregation, document extraction, full-text indexing, and NCGS-compliant proposal generation.

## 🏛️ Tracked Municipal Portals (North Carolina)

| Portal ID | Jurisdiction | County | Portal Type | Specialization |
| :--- | :--- | :--- | :--- | :--- |
| `burke_county` | Burke County, NC | Burke | CivicPlus Bids | Facility HVAC, courthouse retrofits, parks & recreation |
| `wake_county` | Wake County, NC | Wake | Wake Procurement | Research Triangle schools, fire rescue stations, MEP |
| `mecklenburg_county` | Charlotte-Mecklenburg | Mecklenburg | Charlotte eBid | Metrolina transit, water/sewer, municipal complexes |
| `buncombe_county` | Buncombe County, NC | Buncombe | Purchasing Portal | Blue Ridge parks, historic renovations, wastewater |
| `guilford_county` | Guilford County & Greensboro | Guilford | Contract Portal | Piedmont Triad industrial, water treatment, electrical |

---

## 🛠️ Architecture & Components

```
backend/bid_scraper/
├── __init__.py
├── models.py              # Pydantic v2 domain schemas (TenderItem, RFPDocument, etc.)
├── portals.py             # 5 NC county procurement portals registry
├── scrapers.py            # Playwright DOM scraper + resilient certified fixtures
├── db.py                  # SQLite database engine with FTS5 search & schema migration
├── mcp_server.py          # FastMCP / MCPServer tools exposed to AI agents
├── api.py                 # FastAPI REST router (/api/bids)
├── proposal_generator.py  # Statutory NCGS 143-128 public bidding proposal generator
├── cron_sync.py           # Scheduled automated cron aggregation daemon & logging
└── README.md              # Architecture documentation and usage guide
```

---

## 🚀 FastMCP Server Tools (for Daystrom AI Fleet Agents)

The MCP server exposes high-leverage tools for autonomous agents:

1. **`search_tenders`**: Search municipal solicitations across NC with filtering by `query`, `county`, `trade` (`hvac`, `electrical`, `plumbing`, `roofing`, etc.), `min_budget`, `max_budget`, and `status`.
2. **`get_tender_details`**: Retrieve full solicitation specifications, issuing agency, dates, submission deadlines, and contacts for a given tender ID.
3. **`extract_rfp_docs`**: Extract all attached specification PDFs, addenda, and design packages associated with a solicitation.
4. **`trigger_portal_scrape`**: Trigger an on-demand scrape and ingestion cycle across one or all 5 NC county portals.
5. **`generate_bid_proposal`**: Generate an executive summary, scope of work, timeline, and NCGS 143-128 statutory compliance checklist for a tender.
6. **`get_scraper_stats`**: Return aggregate metrics: total opportunities, open bids, and cumulative pipeline budget.

### Starting the MCP Server:
```bash
# Run standalone stdio server for Claude/Cursor/Cline/Devin
python -m backend.bid_scraper.mcp_server
```

---

## 🌐 FastAPI REST Endpoints

Mounted under `/api/bids` on the OmniTender backend:

- `GET /api/bids/search`: Paginated search with county/trade/budget filters.
- `GET /api/bids/stats`: Aggregated metrics (total tenders, open bids, pipeline value).
- `GET /api/bids/portals`: Status and URLs of the 5 tracked NC municipal portals.
- `GET /api/bids/{tender_id}`: Full detail for an individual solicitation.
- `GET /api/bids/{tender_id}/documents`: Attached specs and addenda.
- `POST /api/bids/sync`: Trigger on-demand sync cycle.
- `POST /api/bids/generate-proposal`: Generate structured proposal with NCGS compliance.
- `GET /rfp-search`: Web portal user interface (`rfp-search.html`).

---

## ⏱️ Daily Cron Synchronization

Run scheduled automated scans:

```bash
# One-time manual or system cron job
python backend/bid_scraper/cron_sync.py --once

# Continuous 24-hour daemon
python backend/bid_scraper/cron_sync.py --daemon --interval-hours 24
```

Receipts and sync history are saved to:
- `data/last_cron_sync.json`
- `data/cron_sync.log`

---

## 🧪 Testing

Execute test suite:
```bash
pytest backend/test_bid_scraper.py -v
```
All 27 integration tests verify:
- Database initialization, indexing, and FTS5 search
- Playwright and certified snapshot scraping
- MCP server tool invocations and output formats
- FastAPI REST endpoints
- Statutory proposal generation
- Web link and HTML route integrity
