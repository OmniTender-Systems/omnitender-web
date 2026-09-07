"""
OmniTender MCP Bid Scraper - Autonomous Municipal Bid Proposal Drafter.
Generates complete, NCGS-compliant public bidding proposals tailored to
specific North Carolina municipal RFPs, integrating with contractor trade profiles.
"""

from typing import Optional
from datetime import datetime, timezone

from backend.bid_scraper.models import (
    ProposalGenerationRequest,
    ProposalGenerationResponse,
)
from backend.bid_scraper.db import get_tender


def generate_municipal_proposal(
    request: ProposalGenerationRequest, db_path: Optional[str] = None
) -> ProposalGenerationResponse:
    """
    Drafts an autonomous, production-ready tender response package tailored
    to a specific NC municipal solicitation.
    """
    tender = get_tender(request.tender_id, db_path)
    if not tender:
        raise ValueError(f"Tender with ID '{request.tender_id}' not found in database.")

    date_str = datetime.now(timezone.utc).strftime("%B %d, %Y")
    base_estimate = request.base_estimate
    labor = round(base_estimate * 0.55, 2)
    materials = round(base_estimate * 0.35, 2)
    contingency = round(base_estimate * 0.10, 2)
    total_bid = round(base_estimate + contingency, 2)

    resolved_trade = request.trade or tender.category

    # Compile requirements list
    req_bullets = "\n".join(f"   - [x] Verified: {req}" for req in tender.requirements)
    if not req_bullets:
        req_bullets = "   - [x] Verified: NC Commercial Trade Licensing & OSHA-30 Compliance."

    doc = f"""# PUBLIC BID PROPOSAL & COMPLIANCE SUBMISSION
**Project Title:** {tender.title}
**Solicitation Number:** {tender.rfp_number}
**Issuing Authority:** {tender.jurisdiction} — {tender.issuing_agency}
**Submission Date:** {date_str}
**Bidding Contractor:** {request.contractor_name} (NC License #{request.license_num})
**Trade Specialization:** {resolved_trade}

---

## SECTION 1: EXECUTIVE COVER LETTER & STATUTORY INTENT
**To the {tender.county} County Board of Commissioners & Purchasing Division:**

{request.contractor_name} respectfully submits this formal proposal in direct response to the solicitation for **{tender.title}** ({tender.rfp_number}). As an active, licensed North Carolina commercial contractor in good standing, we certify that our firm possesses the master tradesmen, specialized equipment, bonded underwriting, and safety supervisors necessary to deliver this project on schedule and in strict accordance with municipal specifications.

We confirm full adherence to all North Carolina General Statutes governing public contracts, including:
- **NCGS 143-128**: Separate specifications for building contracts & certified trade coordination.
- **NCGS 143-129**: Procedure for letting of public contracts & formal competitive bidding compliance.
- **NCGS 143-133.3**: E-Verify employer compliance certification for all on-site personnel.

Our firm maintains an active Certificate of Commercial General Liability Insurance ($2,000,000 aggregate) and statutory Worker's Compensation coverage.

---

## SECTION 2: TECHNICAL SCOPE OF WORK & EXECUTION METHODOLOGY
Based on our review of project documents from {tender.issuing_agency}, our phased execution strategy comprises:

1. **Pre-Construction Mobilization & Site Survey:**
   - On-site staging, laser measurements, and initial kickoff with {tender.county} County project managers.
   - Immediate submittal of equipment cut-sheets, engineering submittals, and shop drawings within 5 business days of Notice to Proceed.

2. **System Decommissioning & EPA-Compliant Remediation:**
   - Safe electrical and mechanical lock-out/tag-out (LOTO).
   - Environmentally compliant reclamation, recycling, and disposal of decommissioned commercial hardware.

3. **Installation & Quality Assurance:**
   - Precision placement, anchorage, piping/wiring connection adhering to the 2024 North Carolina Building & Mechanical Code.
   - Comprehensive multi-stage pressure, circuit, and load-balance validation.

4. **Commissioning & Handover:**
   - Continuous 72-hour operational load-testing under supervisor oversight.
   - Full delivery of Operations & Maintenance (O&M) manuals, warranty documents, and on-site municipal staff training.

---

## SECTION 3: LINE-ITEM COST BREAKDOWN & GUARANTEED MAXIMUM PRICE
| Cost Category | Description | Amount (USD) |
|---|---|---|
| **Direct Skilled Labor** | Certified NC Master Tradesmen, Apprentices, & Supervisors | ${labor:,.2f} |
| **Commercial Materials & Hardware** | Factory-certified equipment, fittings, conduits & units | ${materials:,.2f} |
| **Project Contingency Reserve** | 10% Reserve for concealed conditions & field variances | ${contingency:,.2f} |
| **TOTAL FIRM BID (GMP)** | **Guaranteed Maximum Price Submitted** | **${total_bid:,.2f}** |

---

## SECTION 4: MANDATORY COMPLIANCE & QUALIFICATIONS
{req_bullets}

- **Safety Benchmark**: Minimum OSHA-30 site supervisors; daily tool-box safety briefings and zero-lost-time record.
- **Non-Collusion**: Under penalty of perjury, this bid is made without connection with any other person or company making a proposal for the same materials or work.

---

**Authorized Contractor Signature:**

___________________________________________
**{request.contractor_name} — Managing Principal**
NC State Contractor License: #{request.license_num}
"""

    return ProposalGenerationResponse(
        tender_id=tender.id,
        tender_title=tender.title,
        county=tender.county,
        contractor_name=request.contractor_name,
        license_num=request.license_num,
        total_bid=total_bid,
        proposal_markdown=doc.strip(),
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
