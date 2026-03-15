# D-ALL-01: Lead Enrichment Pipeline

## Goal
Automatically enrich every new lead that enters the Leads DB with verified email addresses, phone numbers, owner/decision-maker information, and social profiles. This is the bridge between raw scraped leads and actionable outreach targets.

## Trigger
**Event-driven:** Fires automatically when a new lead is added to the Leads DB with `Status = New`. Can also be run manually on a batch of leads.

## Inputs
- Leads DB entries where `Status = New`
- Required fields: At minimum `Company` name OR `Website` URL
- Optional: `City`, `State` (improves accuracy)

## Process

### Step 1: Read New Leads from Notion
- Query Leads DB via Notion API for all entries where `Status = New`
- Batch into groups of 50 for processing
- Script: `execution/notion_client.py` (read operation)

### Step 2: Website Scraping & Contact Extraction
- For each lead with a website URL:
  - Fetch main page + up to 5 contact pages (/contact, /about, /team, /staff, /people)
  - Use Claude Haiku to extract: owner name, title, emails, phones, social links
  - Script: `execution/scrape_website_contacts.py`
- Cost: ~$0.002 per lead (Claude Haiku extraction)

### Step 3: Email Enrichment via AnyMailFinder
- For leads where Step 2 didn't find a verified email:
  - Run bulk enrichment via AnyMailFinder API
  - For batches >200 leads: Use bulk API endpoint (faster, same cost)
  - For batches <200 leads: Use concurrent individual calls (20 parallel)
  - Script: `execution/enrich_emails.py`
- Cost: ~$0.05 per lead

### Step 4: Update Leads in Notion
- Write enriched data back to Leads DB:
  - `Email` → best verified email
  - `Owner Name` → extracted owner/decision-maker
  - `Owner Title` → their role
  - `Owner Email` → if different from company email
  - `LinkedIn URL` → if found
  - `Phone` → best phone number
  - `Enrichment Status` → 'Complete', 'Partial', or 'Failed'
  - `Status` → 'Enriched'
- Script: `execution/notion_client.py` (update operation)

### Step 5: Log Metrics
- Calculate and log: total leads processed, email hit rate, avg cost per lead, processing time
- Write to Metrics Dashboard DB

## Outputs
- Updated leads in Notion Leads DB with status 'Enriched'
- Metrics entry in Metrics Dashboard DB

## Edge Cases
- **No website URL:** Skip website scraping, go straight to AnyMailFinder with company name + city
- **Website returns 403/503:** Mark `Enrichment Status = Partial`, still attempt AnyMailFinder
- **AnyMailFinder returns no email:** Mark `Enrichment Status = Failed`, lead stays in pipeline but flagged
- **Duplicate detection:** Check `Lead ID` before processing. Skip already-enriched leads.

## Autoresearch Metrics
- **Primary metric:** Email hit rate (% of leads with at least one verified email)
- **Secondary:** Cost per enriched lead, processing time per batch
- **Experiment ideas:** Try different enrichment providers, adjust website scraping depth, test with/without DuckDuckGo web search step

## Dependencies
- `NOTION_API_KEY` in .env
- `ANYMAILFINDER_API_KEY` in .env
- `ANTHROPIC_API_KEY` in .env (for Claude Haiku extraction)
