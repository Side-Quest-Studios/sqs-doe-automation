"""
D-NCL-05: Apollo Business Owner Discovery
==========================================
Searches Apollo's database for business owners matching NCL's ICP,
deduplicates against existing Notion leads, and writes new leads to the Leads DB.

Usage:
    # Test run (10 leads)
    python execution/ncl_discover_leads.py --limit 10
    
    # Full weekly run (200 leads)
    python execution/ncl_discover_leads.py --limit 200
    
    # Dry run (search but don't write to Notion)
    python execution/ncl_discover_leads.py --limit 10 --dry-run

Requires: APOLLO_API_KEY + NOTION_API_KEY in .env
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime

# Add execution/ to path so we can import sibling modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from apollo_client import ApolloClient
from notion_client_sqs import NotionClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger("ncl-discover")


def run_discovery(limit=100, dry_run=False):
    """Run the NCL lead discovery pipeline."""
    
    apollo = ApolloClient()
    notion = NotionClient()
    
    logger.info(f"Starting NCL lead discovery (limit={limit}, dry_run={dry_run})")
    
    # =========================================================================
    # Step 1: Search Apollo for business owners matching NCL ICP
    # =========================================================================
    logger.info("Step 1: Searching Apollo for NCL ICP matches...")
    
    people = apollo.search_people_all(
        max_results=limit,
        titles=["Owner", "Founder", "CEO", "Managing Director", "President",
                "Co-Founder", "Director", "Principal"],
        employee_ranges=["1,10", "11,20", "21,50"],
        locations=["United States"],
        # Industries where AI adoption is low = highest NCL value
        # Apollo uses industry tags, we cast a wide net and filter later
    )
    
    logger.info(f"Apollo returned {len(people)} people")
    
    if not people:
        logger.warning("No results from Apollo. Check API key and filters.")
        return {"leads_found": 0, "leads_new": 0, "leads_written": 0}
    
    # =========================================================================
    # Step 2: Deduplicate against existing Notion Leads DB
    # =========================================================================
    logger.info("Step 2: Deduplicating against existing Notion leads...")
    
    existing_leads = notion.query_leads(brand="No Code Lab", limit=5000)
    existing_companies = set()
    existing_emails = set()
    
    for lead in existing_leads:
        if lead.get("Company"):
            existing_companies.add(lead["Company"].lower().strip())
        if lead.get("Email"):
            existing_emails.add(lead["Email"].lower().strip())
    
    new_people = []
    duplicates = 0
    
    for person in people:
        company = (person.get("company") or "").lower().strip()
        email = (person.get("email") or "").lower().strip()
        
        if company and company in existing_companies:
            duplicates += 1
            continue
        if email and email in existing_emails:
            duplicates += 1
            continue
        
        new_people.append(person)
        # Add to tracking sets to avoid duplicates within this batch
        if company:
            existing_companies.add(company)
        if email:
            existing_emails.add(email)
    
    logger.info(f"Dedup complete: {len(new_people)} new, {duplicates} duplicates skipped")
    
    # =========================================================================
    # Step 3: Write new leads to Notion
    # =========================================================================
    if dry_run:
        logger.info("DRY RUN — Not writing to Notion. Here's what would be written:")
        for p in new_people[:5]:
            print(f"  {p['full_name']} | {p.get('title', 'N/A')} @ {p.get('company', 'N/A')} | {p.get('email', 'No email')}")
        if len(new_people) > 5:
            print(f"  ... and {len(new_people) - 5} more")
        return {"leads_found": len(people), "leads_new": len(new_people), "leads_written": 0}
    
    logger.info(f"Step 3: Writing {len(new_people)} new leads to Notion...")
    
    written = 0
    errors = 0
    
    for i, person in enumerate(new_people):
        try:
            lead_data = ApolloClient.person_to_notion_lead(
                person, brand="No Code Lab", source="Apify Scrape"  # Using "Apify Scrape" since there's no "Apollo" option yet
            )
            notion.create_lead(lead_data)
            written += 1
            
            if (i + 1) % 10 == 0:
                logger.info(f"  Written {i+1}/{len(new_people)} leads...")
                
        except Exception as e:
            logger.error(f"  Failed to write lead {person.get('full_name', '?')}: {e}")
            errors += 1
    
    logger.info(f"Step 3 complete: {written} written, {errors} errors")
    
    # =========================================================================
    # Step 4: Log metrics
    # =========================================================================
    metrics = {
        "leads_found": len(people),
        "leads_new": len(new_people),
        "leads_written": written,
        "duplicates_skipped": duplicates,
        "errors": errors,
        "email_hit_rate": sum(1 for p in new_people if p.get("email")) / max(len(new_people), 1),
    }
    
    logger.info(f"Results: {json.dumps(metrics, indent=2)}")
    
    # Write metrics to Notion Metrics Dashboard
    try:
        notion.log_metrics({
            "Metric Entry": f"NCL Lead Discovery - {datetime.now().strftime('%Y-%m-%d')}",
            "Brand": "No Code Lab",
            "Channel": "Product",
            "Leads Captured": written,
            "Notes": json.dumps(metrics),
        })
        logger.info("Metrics logged to Notion Metrics Dashboard")
    except Exception as e:
        logger.warning(f"Failed to log metrics: {e}")
    
    return metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NCL Lead Discovery (D-NCL-05)")
    parser.add_argument("--limit", type=int, default=100, help="Max leads to search for")
    parser.add_argument("--dry-run", action="store_true", help="Search but don't write to Notion")
    args = parser.parse_args()
    
    results = run_discovery(limit=args.limit, dry_run=args.dry_run)
    
    print(f"\n{'='*50}")
    print(f"D-NCL-05 Complete")
    print(f"  Leads found:   {results['leads_found']}")
    print(f"  New leads:     {results['leads_new']}")
    print(f"  Written:       {results['leads_written']}")
    print(f"{'='*50}")
