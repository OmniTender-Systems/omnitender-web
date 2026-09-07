"""
Unit and integration tests for OmniTender MCP Bid Scraper.
Tests domain models, portal registry, SQLite persistence, scrapers,
NCGS proposal drafting, FastMCP tools, FastAPI REST endpoints, and cron sync.
"""

import os
import json
import pytest
from fastapi.testclient import TestClient

from backend.bid_scraper.models import (
    BidStatus,
    TradeCategory,
    RFPDocument,
    MunicipalPortal,
    TenderItem,
    TenderSearchFilter,
    ProposalGenerationRequest,
)
from backend.bid_scraper.portals import (
    NC_MUNICIPAL_PORTALS,
    get_all_portals,
    get_portal_by_id,
)
from backend.bid_scraper.db import (
    init_db,
    get_connection,
    upsert_tenders,
    search_tenders,
    get_tender,
    get_all_portals_from_db,
    get_stats,
)
from backend.bid_scraper.scrapers import (
    SCRAPER_REGISTRY,
    AggregatorScraper,
    BurkeCountyScraper,
    WakeCountyScraper,
    MecklenburgCountyScraper,
    BuncombeCountyScraper,
    GuilfordCountyScraper,
)
from backend.bid_scraper.proposal_generator import generate_municipal_proposal
from backend.bid_scraper.mcp_server import (
    search_tenders_tool,
    extract_rfp_docs_tool,
    get_tender_details_tool,
    generate_bid_proposal_tool,
    sync_portals_tool,
    list_portals_tool,
    get_municipal_stats_tool,
    server,
)
from backend.bid_scraper.cron_sync import execute_cron_scan
from backend.main import app


@pytest.fixture
def test_db_path(tmp_path):
    """Provides a fresh isolated SQLite database path for testing."""
    db_file = str(tmp_path / "test_bids.db")
    init_db(db_file)
    return db_file


@pytest.fixture
def seeded_db_path(test_db_path):
    """Provides an isolated database pre-seeded with all 5 NC portal items."""
    agg = AggregatorScraper(db_path=test_db_path)
    agg.run_all(use_playwright=False)
    return test_db_path


class TestPortalRegistry:
    def test_five_nc_county_portals_configured(self):
        expected_counties = {"burke_county", "wake_county", "mecklenburg_county", "buncombe_county", "guilford_county"}
        assert set(NC_MUNICIPAL_PORTALS.keys()) == expected_counties
        assert len(get_all_portals()) == 5

    def test_get_portal_by_id(self):
        portal = get_portal_by_id("burke_county")
        assert portal.county == "Burke"
        assert portal.active is True
        assert "burkenc.org" in portal.base_url

    def test_get_portal_invalid_id_raises(self):
        with pytest.raises(KeyError):
            get_portal_by_id("non_existent_county")


class TestDatabaseAndPersistence:
    def test_init_and_portal_seeding(self, test_db_path):
        portals = get_all_portals_from_db(test_db_path)
        assert len(portals) == 5
        counties = {p.county for p in portals}
        assert {"Burke", "Wake", "Mecklenburg", "Buncombe", "Guilford"}.issubset(counties)

    def test_upsert_and_retrieve_tender(self, test_db_path):
        doc = RFPDocument(
            doc_id="doc-test-1",
            name="Test-Spec.pdf",
            url="https://example.gov/test.pdf",
            doc_type="specifications",
            size_bytes=1024,
            content_snippet="Test mechanical spec",
        )
        item = TenderItem(
            id="TEST-001",
            portal_id="burke_county",
            jurisdiction="Burke County, NC",
            county="Burke",
            rfp_number="RFP-TEST-01",
            title="Courthouse Chillers Retrofit",
            description="Complete retrofit of commercial water chillers.",
            category="HVAC",
            trade=TradeCategory.HVAC,
            issuing_agency="Burke Facilities",
            estimated_budget=120000.0,
            status=BidStatus.OPEN,
            source_url="https://example.gov/rfp-test-01",
            documents=[doc],
            requirements=["NC Commercial HVAC License", "OSHA-30"],
        )

        persisted = upsert_tenders([item], test_db_path)
        assert persisted == 1

        retrieved = get_tender("TEST-001", test_db_path)
        assert retrieved is not None
        assert retrieved.title == "Courthouse Chillers Retrofit"
        assert retrieved.estimated_budget == 120000.0
        assert len(retrieved.documents) == 1
        assert retrieved.documents[0].name == "Test-Spec.pdf"
        assert "OSHA-30" in retrieved.requirements

    def test_search_filtering(self, seeded_db_path):
        # Search by county
        burke_filter = TenderSearchFilter(county="Burke")
        results, total = search_tenders(burke_filter, seeded_db_path)
        assert total > 0
        assert all(t.county == "Burke" for t in results)

        # Search by trade
        hvac_filter = TenderSearchFilter(trade="hvac")
        results, total = search_tenders(hvac_filter, seeded_db_path)
        assert total > 0
        assert all(t.trade == TradeCategory.HVAC for t in results)

        # Search by budget range
        budget_filter = TenderSearchFilter(min_budget=100000.0, max_budget=300000.0)
        results, total = search_tenders(budget_filter, seeded_db_path)
        assert total > 0
        for t in results:
            assert t.estimated_budget is not None
            assert 100000.0 <= t.estimated_budget <= 300000.0

        # Search keyword query
        query_filter = TenderSearchFilter(query="Boiler")
        results, total = search_tenders(query_filter, seeded_db_path)
        assert total > 0
        assert any("Boiler" in (t.title + t.description) for t in results)

    def test_get_stats(self, seeded_db_path):
        stats = get_stats(seeded_db_path)
        assert stats["total_tenders"] >= 10
        assert stats["open_tenders"] >= 10
        assert stats["total_open_budget_est"] > 1000000
        assert len(stats["by_county"]) == 5
        assert "Burke" in stats["by_county"]


class TestScrapers:
    def test_individual_scrapers(self):
        scrapers = [
            BurkeCountyScraper(),
            WakeCountyScraper(),
            MecklenburgCountyScraper(),
            BuncombeCountyScraper(),
            GuilfordCountyScraper(),
        ]
        for scraper in scrapers:
            items = scraper.scrape(use_playwright=False)
            assert len(items) >= 2
            for item in items:
                assert item.portal_id == scraper.portal.portal_id
                assert item.title
                assert item.source_url.startswith("http")

    def test_aggregator_run_all(self, test_db_path):
        agg = AggregatorScraper(db_path=test_db_path)
        summary = agg.run_all(use_playwright=False)
        assert summary["portals_scraped"] == 5
        assert summary["total_bids_collected"] >= 10
        assert summary["total_bids_persisted"] >= 10
        assert len(summary["portal_breakdown"]) == 5


class TestProposalGenerator:
    def test_generate_proposal_success(self, seeded_db_path):
        req = ProposalGenerationRequest(
            tender_id="NC-BURKE-2026-001",
            contractor_name="Carolina Thermal & Mechanical LLC",
            license_num="NC-H3-99882",
            base_estimate=150000.0,
            trade="HVAC Mechanical",
        )
        resp = generate_municipal_proposal(req, db_path=seeded_db_path)
        assert resp.tender_id == "NC-BURKE-2026-001"
        assert resp.county == "Burke"
        assert resp.total_bid == 165000.0  # 150000 + 10% contingency
        assert "NCGS 143-128" in resp.proposal_markdown
        assert "Carolina Thermal & Mechanical LLC" in resp.proposal_markdown
        assert "NC-H3-99882" in resp.proposal_markdown
        assert "Guaranteed Maximum Price" in resp.proposal_markdown

    def test_generate_proposal_invalid_tender_raises(self, seeded_db_path):
        req = ProposalGenerationRequest(
            tender_id="INVALID-TENDER-ID",
            contractor_name="Ghost Contractor",
            license_num="NC-00000",
            base_estimate=50000.0,
        )
        with pytest.raises(ValueError, match="not found"):
            generate_municipal_proposal(req, db_path=seeded_db_path)


class TestMCPServerTools:
    def test_mcp_server_instance(self):
        assert server is not None
        assert server.name == "OmniTender-Municipal-Bid-Scraper"

    def test_search_tenders_tool(self):
        res_str = search_tenders_tool(county="Burke")
        data = json.loads(res_str)
        assert "total_found" in data
        assert data["total_found"] > 0
        assert len(data["tenders"]) > 0
        assert data["tenders"][0]["county"] == "Burke"

    def test_extract_rfp_docs_tool(self):
        res_str = extract_rfp_docs_tool("NC-BURKE-2026-001")
        data = json.loads(res_str)
        assert data["tender_id"] == "NC-BURKE-2026-001"
        assert "documents" in data
        assert len(data["documents"]) >= 2
        assert "requirements" in data
        assert len(data["requirements"]) > 0

    def test_get_tender_details_tool(self):
        res_str = get_tender_details_tool("NC-BURKE-2026-001")
        data = json.loads(res_str)
        assert data["id"] == "NC-BURKE-2026-001"
        assert "title" in data
        assert "description" in data

    def test_generate_bid_proposal_tool(self):
        res_str = generate_bid_proposal_tool(
            tender_id="NC-BURKE-2026-001",
            contractor_name="Apex Mechanical Inc",
            license_num="NC-H2-12345",
            base_estimate=120000.0,
        )
        data = json.loads(res_str)
        assert data["tender_id"] == "NC-BURKE-2026-001"
        assert data["total_bid"] == 132000.0
        assert "NCGS 143-128" in data["proposal_markdown"]

    def test_list_portals_tool(self):
        res_str = list_portals_tool()
        data = json.loads(res_str)
        assert len(data) == 5
        portal_ids = {p["portal_id"] for p in data}
        assert "wake_county" in portal_ids

    def test_get_municipal_stats_tool(self):
        res_str = get_municipal_stats_tool()
        data = json.loads(res_str)
        assert data["total_tenders"] >= 10
        assert "by_county" in data


class TestFastAPIBidEndpoints:
    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_search_endpoint(self, client):
        resp = client.get("/api/bids/search?county=Wake")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] > 0
        for item in data["results"]:
            assert item["county"] == "Wake"

    def test_stats_endpoint(self, client):
        resp = client.get("/api/bids/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_tenders"] >= 10

    def test_portals_endpoint(self, client):
        resp = client.get("/api/bids/portals")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 5

    def test_tender_detail_and_docs(self, client):
        resp = client.get("/api/bids/NC-BURKE-2026-001")
        assert resp.status_code == 200
        item = resp.json()
        assert item["id"] == "NC-BURKE-2026-001"

        docs_resp = client.get("/api/bids/NC-BURKE-2026-001/documents")
        assert docs_resp.status_code == 200
        docs = docs_resp.json()
        assert len(docs) >= 2

    def test_tender_not_found(self, client):
        resp = client.get("/api/bids/NON-EXISTENT-ID")
        assert resp.status_code == 404

    def test_sync_endpoint(self, client):
        resp = client.post("/api/bids/sync")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "SUCCESS"
        assert data["portals_scraped"] == 5

    def test_proposal_generation_endpoint(self, client):
        payload = {
            "tender_id": "NC-BURKE-2026-001",
            "contractor_name": "Triad Fire & HVAC",
            "license_num": "NC-M-55441",
            "base_estimate": 80000.0,
            "trade": "Mechanical",
        }
        resp = client.post("/api/bids/proposals/generate", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_bid"] == 88000.0
        assert "Triad Fire & HVAC" in data["proposal_markdown"]

    def test_html_ui_routes(self, client):
        bids_page = client.get("/bids")
        assert bids_page.status_code == 200
        assert "OmniTender" in bids_page.text

        rfp_search_page = client.get("/rfp-search")
        assert rfp_search_page.status_code == 200
        assert "FastMCP" in rfp_search_page.text


class TestCronSync:
    def test_cron_scan_execution(self, test_db_path):
        receipt = execute_cron_scan(use_playwright=False, db_path=test_db_path, output_receipt=False)
        assert receipt["status"] == "SUCCESS"
        assert receipt["portals_scanned"] == 5
        assert receipt["total_bids_collected"] >= 10
        assert receipt["total_bids_persisted"] >= 10
        assert receipt["database_totals"]["total_tenders"] >= 10
