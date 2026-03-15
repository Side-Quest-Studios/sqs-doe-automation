"""
Notion Client for SQS DOE Automation
=====================================
Read and write to Notion databases via the official API.
Replaces Google Sheets as the data layer.

Usage:
    from notion_client_sqs import NotionClient
    client = NotionClient()
    
    # Read leads
    leads = client.query_leads(brand="No Code Lab", status="New")
    
    # Create a lead
    client.create_lead({
        "Lead Name": "John Smith",
        "Company": "Smith Consulting",
        "Brand": "No Code Lab",
        "Status": "New",
        "Lead Source": "Apollo",
        ...
    })
    
    # Update a lead
    client.update_lead(page_id, {"Status": "Enriched", "Email": "john@smith.com"})

Requires: NOTION_API_KEY in .env
"""

import os
import json
import time
import logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("notion-client")

try:
    import requests
except ImportError:
    raise ImportError("Install requests: pip install requests")

NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_VERSION = "2022-06-28"

# Database IDs from .env
DB_IDS = {
    "leads": os.getenv("NOTION_DB_LEADS", "802e397dc5cc48d3b2ca0ac99cdd0bc7"),
    "campaigns": os.getenv("NOTION_DB_CAMPAIGNS", "b17603d0fe5b450cb6bf29883b8f36d8"),
    "content": os.getenv("NOTION_DB_CONTENT", "5d01e5092f4645d596a88470720cdc35"),
    "directives": os.getenv("NOTION_DB_DIRECTIVES", "b216eec6274e46bda07a304cec3fffcf"),
    "experiments": os.getenv("NOTION_DB_EXPERIMENTS", "7ea6ca9fc83543f4b9a33500a4d3b17e"),
    "metrics": os.getenv("NOTION_DB_METRICS", "02f98090fb374d95bce14b82d0d8e68c"),
    "roadmap": os.getenv("NOTION_DB_ROADMAP", "05729f396ea94f58abfa9f8cb2f9f5fa"),
}

# NCL-specific database IDs
NCL_DB_IDS = {
    "cold_leads": os.getenv("NOTION_NCL_COLD_LEADS", "afc89a581d9a47979b8bb5b208258faf"),
    "content_pipeline": os.getenv("NOTION_NCL_CONTENT_PIPELINE", "3211686ea89c81e8884ac86f4775ebaa"),
}


class NotionClient:
    """Client for reading/writing SQS Notion databases."""

    def __init__(self, api_key=None):
        self.api_key = api_key or NOTION_API_KEY
        if not self.api_key:
            raise ValueError(
                "NOTION_API_KEY not found. Set it in .env or pass to NotionClient()"
            )
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Notion-Version": NOTION_VERSION,
        }
        self.base_url = "https://api.notion.com/v1"

    # =========================================================================
    # LOW-LEVEL API
    # =========================================================================

    def _request(self, method, endpoint, data=None, retries=3):
        """Make an API request with retry logic."""
        url = f"{self.base_url}/{endpoint}"
        for attempt in range(retries):
            try:
                resp = requests.request(
                    method, url, headers=self.headers, json=data, timeout=30
                )
                if resp.status_code == 429:
                    wait = int(resp.headers.get("Retry-After", 2))
                    logger.warning(f"Rate limited. Waiting {wait}s...")
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                return resp.json()
            except requests.exceptions.RequestException as e:
                if attempt == retries - 1:
                    raise
                logger.warning(f"Request failed (attempt {attempt+1}): {e}")
                time.sleep(2 ** attempt)

    def query_database(self, database_id, filter_obj=None, sorts=None, page_size=100):
        """Query a Notion database with optional filters and sorts.
        Returns list of page objects.
        """
        data = {"page_size": min(page_size, 100)}
        if filter_obj:
            data["filter"] = filter_obj
        if sorts:
            data["sorts"] = sorts

        all_results = []
        has_more = True
        start_cursor = None

        while has_more:
            if start_cursor:
                data["start_cursor"] = start_cursor
            result = self._request("POST", f"databases/{database_id}/query", data)
            all_results.extend(result.get("results", []))
            has_more = result.get("has_more", False)
            start_cursor = result.get("next_cursor")
            if len(all_results) >= page_size:
                break

        return all_results

    def create_page(self, database_id, properties):
        """Create a new page in a Notion database."""
        data = {
            "parent": {"database_id": database_id},
            "properties": self._build_properties(properties),
        }
        return self._request("POST", "pages", data)

    def update_page(self, page_id, properties):
        """Update an existing page's properties."""
        data = {"properties": self._build_properties(properties)}
        return self._request("PATCH", f"pages/{page_id}", data)

    # =========================================================================
    # PROPERTY BUILDERS
    # =========================================================================

    def _build_properties(self, props):
        """Convert simple key-value pairs to Notion property format."""
        notion_props = {}
        for key, value in props.items():
            if value is None:
                continue
            notion_props[key] = self._build_single_property(key, value)
        return notion_props

    def _build_single_property(self, key, value):
        """Build a single Notion property value."""
        # Title
        if key in ("Lead Name", "Campaign Name", "Title", "Directive Name",
                    "Experiment", "Metric Entry", "Task"):
            return {"title": [{"text": {"content": str(value)}}]}

        # Select
        if key in ("Brand", "Status", "Lead Source", "Type", "Platform",
                    "Enrichment Status", "Category", "Trigger", "Frequency",
                    "Priority", "Layer", "Result", "Content Type", "Pillar",
                    "Channel"):
            return {"select": {"name": str(value)}}

        # Multi-select (pass as list or JSON string)
        if key in ("Brand",) and isinstance(value, list):
            return {"multi_select": [{"name": v} for v in value]}

        # Number
        if key in ("ICP Match Score", "Emails Sent", "Open Rate", "Reply Rate",
                    "Positive Replies", "Leads Generated", "Impressions",
                    "Engagement", "Clicks", "Followers", "Engagement Rate",
                    "Leads Captured", "Signups", "Revenue", "Cost",
                    "Metric Before", "Metric After", "Delta", "Version",
                    "Current Score", "Best Score"):
            return {"number": float(value) if value else None}

        # URL
        if key in ("Website", "LinkedIn URL"):
            return {"url": str(value) if value else None}

        # Email
        if key in ("Email", "Owner Email"):
            return {"email": str(value) if value else None}

        # Phone
        if key in ("Phone",):
            return {"phone_number": str(value) if value else None}

        # Rich text (default for everything else)
        return {"rich_text": [{"text": {"content": str(value)}}]}

    # =========================================================================
    # PROPERTY EXTRACTORS
    # =========================================================================

    @staticmethod
    def extract_properties(page):
        """Extract simple key-value pairs from a Notion page object."""
        props = {}
        props["page_id"] = page["id"]
        for key, prop in page.get("properties", {}).items():
            props[key] = NotionClient._extract_value(prop)
        return props

    @staticmethod
    def _extract_value(prop):
        """Extract a simple value from a Notion property."""
        ptype = prop.get("type")
        if ptype == "title":
            parts = prop.get("title", [])
            return "".join(p.get("text", {}).get("content", "") for p in parts)
        elif ptype == "rich_text":
            parts = prop.get("rich_text", [])
            return "".join(p.get("text", {}).get("content", "") for p in parts)
        elif ptype == "select":
            sel = prop.get("select")
            return sel["name"] if sel else None
        elif ptype == "multi_select":
            return [s["name"] for s in prop.get("multi_select", [])]
        elif ptype == "number":
            return prop.get("number")
        elif ptype == "url":
            return prop.get("url")
        elif ptype == "email":
            return prop.get("email")
        elif ptype == "phone_number":
            return prop.get("phone_number")
        elif ptype == "checkbox":
            return prop.get("checkbox")
        elif ptype == "date":
            date = prop.get("date")
            return date["start"] if date else None
        elif ptype == "created_time":
            return prop.get("created_time")
        elif ptype == "last_edited_time":
            return prop.get("last_edited_time")
        elif ptype == "unique_id":
            uid = prop.get("unique_id", {})
            prefix = uid.get("prefix", "")
            number = uid.get("number", "")
            return f"{prefix}-{number}" if prefix else str(number)
        return None

    # =========================================================================
    # HIGH-LEVEL: LEADS
    # =========================================================================

    def query_leads(self, brand=None, status=None, limit=100):
        """Query leads with optional brand and status filters."""
        filters = []
        if brand:
            filters.append({
                "property": "Brand",
                "select": {"equals": brand}
            })
        if status:
            filters.append({
                "property": "Status",
                "select": {"equals": status}
            })

        filter_obj = None
        if len(filters) == 1:
            filter_obj = filters[0]
        elif len(filters) > 1:
            filter_obj = {"and": filters}

        pages = self.query_database(DB_IDS["leads"], filter_obj, page_size=limit)
        return [self.extract_properties(p) for p in pages]

    def create_lead(self, lead_data):
        """Create a new lead in the Leads DB."""
        return self.create_page(DB_IDS["leads"], lead_data)

    def update_lead(self, page_id, updates):
        """Update an existing lead."""
        return self.update_page(page_id, updates)

    def lead_exists(self, company, city=None):
        """Check if a lead already exists (deduplication)."""
        filter_obj = {
            "property": "Company",
            "rich_text": {"equals": company}
        }
        if city:
            filter_obj = {
                "and": [
                    filter_obj,
                    {"property": "City", "rich_text": {"equals": city}}
                ]
            }
        results = self.query_database(DB_IDS["leads"], filter_obj, page_size=1)
        return len(results) > 0

    # =========================================================================
    # HIGH-LEVEL: CAMPAIGNS
    # =========================================================================

    def create_campaign(self, campaign_data):
        """Create a new outreach campaign."""
        return self.create_page(DB_IDS["campaigns"], campaign_data)

    def update_campaign(self, page_id, updates):
        """Update campaign metrics."""
        return self.update_page(page_id, updates)

    # =========================================================================
    # HIGH-LEVEL: CONTENT
    # =========================================================================

    def create_content(self, content_data):
        """Create a new content piece in the Content Library."""
        return self.create_page(DB_IDS["content"], content_data)

    # =========================================================================
    # HIGH-LEVEL: METRICS
    # =========================================================================

    def log_metrics(self, metrics_data):
        """Log a metrics entry to the Metrics Dashboard."""
        return self.create_page(DB_IDS["metrics"], metrics_data)

    # =========================================================================
    # HIGH-LEVEL: EXPERIMENTS
    # =========================================================================

    def log_experiment(self, experiment_data):
        """Log an experiment result to the Experiment Log."""
        return self.create_page(DB_IDS["experiments"], experiment_data)


# =============================================================================
# CLI USAGE
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="SQS Notion Client")
    parser.add_argument("action", choices=["test", "query-leads", "count-leads"])
    parser.add_argument("--brand", default=None)
    parser.add_argument("--status", default=None)
    args = parser.parse_args()

    client = NotionClient()

    if args.action == "test":
        print("Testing Notion connection...")
        leads = client.query_leads(limit=1)
        print(f"Connection OK. Found {len(leads)} lead(s) in database.")
        print(f"Database IDs configured: {list(DB_IDS.keys())}")

    elif args.action == "query-leads":
        leads = client.query_leads(brand=args.brand, status=args.status)
        for lead in leads:
            print(f"  {lead.get('Lead Name', 'N/A')} | {lead.get('Company', 'N/A')} | {lead.get('Status', 'N/A')}")
        print(f"\nTotal: {len(leads)} leads")

    elif args.action == "count-leads":
        leads = client.query_leads(brand=args.brand, status=args.status)
        print(f"Leads: {len(leads)} (brand={args.brand}, status={args.status})")
