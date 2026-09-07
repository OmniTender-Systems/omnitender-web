"""
OmniTender MCP Bid Scraper - 5 North Carolina Municipal Portals Registry.
Defines portal metadata, target URLs, selectors, and trade configurations
for Burke, Wake, Mecklenburg, Buncombe, and Guilford counties.
"""

from typing import Dict, List
from backend.bid_scraper.models import MunicipalPortal

NC_MUNICIPAL_PORTALS: Dict[str, MunicipalPortal] = {
    "burke_county": MunicipalPortal(
        portal_id="burke_county",
        name="Burke County Procurement & General Services",
        jurisdiction="Burke County, NC",
        county="Burke",
        base_url="https://www.burkenc.org/bids.aspx",
        portal_type="civicplus_bids",
        active=True,
        notes="Western NC municipal hub; heavy focus on facility HVAC, courthouse renovations, and public parks.",
    ),
    "wake_county": MunicipalPortal(
        portal_id="wake_county",
        name="Wake County Procurement & Solicitations",
        jurisdiction="Wake County, NC",
        county="Wake",
        base_url="https://www.wake.gov/departments-government/finance/current-business-opportunities",
        portal_type="wake_procurement",
        active=True,
        notes="Research Triangle epicenter; major public school HVAC, fire stations, and library MEP modernizations.",
    ),
    "mecklenburg_county": MunicipalPortal(
        portal_id="mecklenburg_county",
        name="Charlotte-Mecklenburg Procurement Services",
        jurisdiction="Mecklenburg County, NC",
        county="Mecklenburg",
        base_url="https://charlottenc.gov/Procurement/Pages/default.aspx",
        portal_type="charlotte_ebid",
        active=True,
        notes="Metrolina commercial leader; transit infrastructure, airport water/sewer, and commercial complexes.",
    ),
    "buncombe_county": MunicipalPortal(
        portal_id="buncombe_county",
        name="Buncombe County General Services Purchasing",
        jurisdiction="Buncombe County, NC",
        county="Buncombe",
        base_url="https://www.buncombecounty.org/governing/depts/budget/purchasing.aspx",
        portal_type="buncombe_purchasing",
        active=True,
        notes="Blue Ridge mountain hub; parks & recreation modernization, historical facilities, and wastewater upgrades.",
    ),
    "guilford_county": MunicipalPortal(
        portal_id="guilford_county",
        name="Guilford County & City of Greensboro Procurement",
        jurisdiction="Guilford County, NC",
        county="Guilford",
        base_url="https://www.guilfordcountync.gov/our-county/purchasing",
        portal_type="guilford_contracts",
        active=True,
        notes="Piedmont Triad industrial/municipal center; water treatment plants, electrical switchgear, emergency medical.",
    ),
}


def get_all_portals() -> List[MunicipalPortal]:
    """Returns list of all configured NC municipal portals."""
    return list(NC_MUNICIPAL_PORTALS.values())


def get_portal_by_id(portal_id: str) -> MunicipalPortal:
    """Returns a specific portal configuration by its unique ID."""
    if portal_id not in NC_MUNICIPAL_PORTALS:
        raise KeyError(f"Portal '{portal_id}' not found. Available portals: {list(NC_MUNICIPAL_PORTALS.keys())}")
    return NC_MUNICIPAL_PORTALS[portal_id]
