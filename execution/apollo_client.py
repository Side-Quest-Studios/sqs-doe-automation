"""
Apollo.io Client for SQS DOE Automation
========================================
Handles lead discovery, email enrichment, and cold email sequences via Apollo API.
Replaces AnyMailFinder ($49/mo) + Instantly ($30-77/mo) with one $59/mo tool.

Usage:
    from apollo_client import ApolloClient
    client = ApolloClient()
    
    # Search for leads matching NCL's ICP
    leads = client.search_people(
        titles=["Owner", "Founder", "CEO"],
        employee_ranges=["1,10", "11,20", "21,50"],
        locations=["United States"],
        industries=["Professional Services", "Real Estate", "Healthcare"]
    )
    
    # Enrich a lead with email
    enriched = client.enrich_person(
        first_name="John",
        last_name="Smith", 
        domain="smithconsulting.com"
    )

Requires: APOLLO_API_KEY in .env
"""

import os
import json
import time
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("apollo-client")

try:
    import requests
except ImportError:
    raise ImportError("Install requests: pip install requests")

APOLLO_API_KEY = os.getenv("APOLLO_API_KEY")


class ApolloClient:
    """Client for Apollo.io lead discovery and enrichment."""

    def __init__(self, api_key=None):
        self.api_key = api_key or APOLLO_API_KEY
        if not self.api_key:
            raise ValueError(
                "APOLLO_API_KEY not found. Set it in .env or pass to ApolloClient()"
            )
        self.base_url = "https://api.apollo.io/api/v1"
        self.headers = {
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
            "X-Api-Key": self.api_key,
        }

    def _request(self, method, endpoint, data=None, retries=3):
        """Make an API request with retry logic and rate limiting."""
        url = f"{self.base_url}/{endpoint}"
        if data is None:
            data = {}

        for attempt in range(retries):
            try:
                if method == "GET":
                    resp = requests.get(url, headers=self.headers, params=data, timeout=30)
                else:
                    resp = requests.post(url, headers=self.headers, json=data, timeout=30)

                if resp.status_code == 429:
                    wait = int(resp.headers.get("Retry-After", 5))
                    logger.warning(f"Rate limited. Waiting {wait}s...")
                    time.sleep(wait)
                    continue

                if resp.status_code == 422:
                    logger.error(f"Validation error: {resp.text}")
                    return None

                resp.raise_for_status()
                return resp.json()

            except requests.exceptions.RequestException as e:
                if attempt == retries - 1:
                    logger.error(f"Request failed after {retries} attempts: {e}")
                    raise
                logger.warning(f"Request failed (attempt {attempt+1}): {e}")
                time.sleep(2 ** attempt)

    # =========================================================================
    # PEOPLE SEARCH (Lead Discovery)
    # =========================================================================

    def search_people(
        self,
        titles=None,
        employee_ranges=None,
        locations=None,
        industries=None,
        keywords=None,
        per_page=25,
        page=1,
    ):
        """Search Apollo's 210M+ database for people matching criteria.
        
        Args:
            titles: List of job titles (e.g., ["Owner", "Founder", "CEO"])
            employee_ranges: List of ranges (e.g., ["1,10", "11,20", "21,50"])
            locations: List of locations (e.g., ["United States", "Mexico"])
            industries: List of industries
            keywords: Keyword search across all fields
            per_page: Results per page (max 100)
            page: Page number
            
        Returns:
            List of person dicts with name, title, company, email, etc.
        """
        data = {
            "per_page": min(per_page, 100),
            "page": page,
        }

        if titles:
            data["person_titles"] = titles
        if employee_ranges:
            data["organization_num_employees_ranges"] = employee_ranges
        if locations:
            data["person_locations"] = locations
        if industries:
            data["organization_industry_tag_ids"] = industries
        if keywords:
            data["q_keywords"] = keywords

        result = self._request("POST", "mixed_people/api_search", data)
        if not result:
            return []

        people = result.get("people", [])
        total = result.get("pagination", {}).get("total_entries", 0)
        logger.info(f"Found {total} total matches, returned {len(people)} on page {page}")

        return [self._normalize_person(p) for p in people]

    def search_people_all(self, max_results=200, **kwargs):
        """Search and paginate through all results up to max_results."""
        all_people = []
        page = 1
        per_page = min(100, max_results)

        while len(all_people) < max_results:
            people = self.search_people(per_page=per_page, page=page, **kwargs)
            if not people:
                break
            all_people.extend(people)
            page += 1
            time.sleep(0.5)  # Respect rate limits

        return all_people[:max_results]

    # =========================================================================
    # ENRICHMENT (Find Email for a Person)
    # =========================================================================

    def enrich_person(self, first_name=None, last_name=None, domain=None,
                      email=None, linkedin_url=None):
        """Enrich a person's contact info via Apollo.
        
        Provide at least: (first_name + last_name + domain) OR email OR linkedin_url
        
        Returns:
            Dict with enriched person data including email, phone, title, etc.
        """
        data = {}
        if first_name:
            data["first_name"] = first_name
        if last_name:
            data["last_name"] = last_name
        if domain:
            data["domain"] = domain
        if email:
            data["email"] = email
        if linkedin_url:
            data["linkedin_url"] = linkedin_url

        result = self._request("POST", "people/match", data)
        if not result or not result.get("person"):
            return None

        return self._normalize_person(result["person"])

    def enrich_batch(self, people_list, delay=0.3):
        """Enrich a list of people. Each item should have first_name, last_name, domain.
        
        Args:
            people_list: List of dicts with enrichment params
            delay: Seconds between API calls (rate limiting)
            
        Returns:
            List of enriched person dicts (None for failures)
        """
        results = []
        for i, person in enumerate(people_list):
            logger.info(f"Enriching {i+1}/{len(people_list)}: {person.get('first_name', '')} {person.get('last_name', '')}")
            try:
                enriched = self.enrich_person(**person)
                results.append(enriched)
            except Exception as e:
                logger.warning(f"Enrichment failed for {person}: {e}")
                results.append(None)
            time.sleep(delay)

        success = sum(1 for r in results if r and r.get("email"))
        logger.info(f"Enrichment complete: {success}/{len(people_list)} emails found ({success/len(people_list)*100:.0f}%)")
        return results

    # =========================================================================
    # EMAIL SEQUENCES (Cold Email)
    # =========================================================================

    def list_sequences(self):
        """List all email sequences."""
        result = self._request("GET", "emailer_campaigns/search")
        if not result:
            return []
        return result.get("emailer_campaigns", [])

    def add_to_sequence(self, sequence_id, contacts):
        """Add contacts to an email sequence.
        
        Args:
            sequence_id: Apollo sequence ID
            contacts: List of dicts with at least 'email' field.
                      Optional: first_name, last_name, custom fields
        """
        data = {
            "emailer_campaign_id": sequence_id,
            "contact_emails": [c["email"] for c in contacts if c.get("email")],
            "send_email_from_email_account_id": None,  # Uses default
        }
        return self._request("POST", "emailer_campaigns/add_contact_ids", data)

    # =========================================================================
    # ORGANIZATION SEARCH
    # =========================================================================

    def search_organizations(self, keywords=None, locations=None,
                              employee_ranges=None, per_page=25):
        """Search for organizations matching criteria."""
        data = {"per_page": min(per_page, 100)}
        if keywords:
            data["q_organization_keyword_tags"] = keywords
        if locations:
            data["organization_locations"] = locations
        if employee_ranges:
            data["organization_num_employees_ranges"] = employee_ranges

        result = self._request("POST", "mixed_companies/search", data)
        if not result:
            return []
        return result.get("organizations", [])

    # =========================================================================
    # HELPERS
    # =========================================================================

    @staticmethod
    def _normalize_person(person):
        """Normalize Apollo person data to a flat dict matching our Notion schema."""
        org = person.get("organization", {}) or {}
        return {
            "first_name": person.get("first_name", ""),
            "last_name": person.get("last_name", ""),
            "full_name": person.get("name", ""),
            "email": person.get("email"),
            "email_status": person.get("email_status"),  # verified, guessed, etc.
            "title": person.get("title", ""),
            "company": org.get("name", ""),
            "company_domain": org.get("primary_domain", ""),
            "company_website": org.get("website_url", ""),
            "industry": org.get("industry", ""),
            "employee_count": org.get("estimated_num_employees"),
            "city": person.get("city", ""),
            "state": person.get("state", ""),
            "country": person.get("country", ""),
            "linkedin_url": person.get("linkedin_url", ""),
            "phone": person.get("phone_number"),
            "company_linkedin": org.get("linkedin_url", ""),
            "company_phone": org.get("phone", ""),
            "apollo_id": person.get("id", ""),
        }

    @staticmethod
    def person_to_notion_lead(person, brand="No Code Lab", source="Apollo"):
        """Convert an Apollo person dict to Notion Leads DB format."""
        return {
            "Lead Name": person.get("full_name", f"{person.get('first_name', '')} {person.get('last_name', '')}").strip(),
            "Company": person.get("company", ""),
            "Email": person.get("email"),
            "Phone": person.get("phone"),
            "Brand": brand,
            "Lead Source": source,
            "Status": "New" if not person.get("email") else "New",
            "Industry": person.get("industry", ""),
            "City": person.get("city", ""),
            "State": person.get("state", ""),
            "Website": person.get("company_website", ""),
            "LinkedIn URL": person.get("linkedin_url", ""),
            "Owner Name": person.get("full_name", ""),
            "Owner Title": person.get("title", ""),
            "Owner Email": person.get("email"),
            "Enrichment Status": "Complete" if person.get("email") else "Pending",
            "Notes": f"Apollo ID: {person.get('apollo_id', '')}. Employees: {person.get('employee_count', 'N/A')}.",
        }


# =============================================================================
# CLI USAGE
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="SQS Apollo Client")
    parser.add_argument("action", choices=["test", "search-ncl", "enrich", "list-sequences"])
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--first-name", default=None)
    parser.add_argument("--last-name", default=None)
    parser.add_argument("--domain", default=None)
    args = parser.parse_args()

    client = ApolloClient()

    if args.action == "test":
        print("Testing Apollo connection...")
        # Simple test: search for 1 person
        people = client.search_people(
            titles=["Owner", "Founder", "CEO"],
            employee_ranges=["1,10"],
            locations=["United States"],
            per_page=1
        )
        if people:
            print(f"Connection OK. Sample: {people[0]['full_name']} at {people[0]['company']}")
        else:
            print("Connection OK but no results returned.")

    elif args.action == "search-ncl":
        print(f"Searching Apollo for NCL ICP (limit={args.limit})...")
        people = client.search_people(
            titles=["Owner", "Founder", "CEO", "Managing Director", "President"],
            employee_ranges=["1,10", "11,20", "21,50"],
            locations=["United States"],
            per_page=args.limit,
        )
        for p in people:
            email_status = f" [{p['email_status']}]" if p.get('email_status') else ""
            print(f"  {p['full_name']} | {p['title']} @ {p['company']} | {p.get('email', 'N/A')}{email_status}")
        print(f"\nTotal: {len(people)} leads found")

    elif args.action == "enrich":
        if not args.first_name or not args.last_name or not args.domain:
            print("Usage: --first-name John --last-name Smith --domain example.com")
        else:
            print(f"Enriching {args.first_name} {args.last_name} @ {args.domain}...")
            result = client.enrich_person(args.first_name, args.last_name, args.domain)
            if result:
                print(f"  Email: {result.get('email', 'N/A')} ({result.get('email_status', '')})")
                print(f"  Title: {result.get('title', 'N/A')}")
                print(f"  Phone: {result.get('phone', 'N/A')}")
            else:
                print("  No match found.")

    elif args.action == "list-sequences":
        print("Listing Apollo email sequences...")
        sequences = client.list_sequences()
        for s in sequences:
            print(f"  {s.get('name', 'Unnamed')} (ID: {s.get('id', '')})")
        print(f"\nTotal: {len(sequences)} sequences")
