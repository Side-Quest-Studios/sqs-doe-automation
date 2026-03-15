# D-SIN-04: Sheet It Now Accountant Google Maps Scraper

## Goal
Scrape accounting firms, bookkeepers, and CPAs from Google Maps across US metros. These are Sheet It Now's primary ICP — professionals who manually convert PDF bank statements to Excel. Write to Leads DB tagged as Sheet It Now.

## Trigger
**Scheduled:** Runs every Wednesday at 5:00 AM ET via Modal cron job.
Manual: `python execution/gmaps_lead_pipeline.py --brand sheetItNow`

## Inputs
- **Search queries (rotate):** "accounting firm", "bookkeeper", "CPA firm", "tax preparation"
- **Target metros (rotate weekly):**
  - Week 1: Miami FL, Fort Lauderdale FL
  - Week 2: New York NY, Newark NJ
  - Week 3: Los Angeles CA, San Diego CA
  - Week 4: Chicago IL, Houston TX
  - Week 5: Atlanta GA, Dallas TX
  - Then repeat
- **Filters:** Min 5 Google reviews, must have website, 2-20 employees preferred
- **Volume:** 50–100 leads per metro, 100–200 per weekly run

## Process

### Step 1: Test Scrape
- Run with `--limit 10` for first metro
- Verify >80% are actual accounting/bookkeeping firms
- If match rate low, try "CPA" or "bookkeeping services" instead

### Step 2: Full Scrape
- Run `execution/gmaps_lead_pipeline.py` for each metro
- Uses Apify `compass/crawler-google-places`
- Output: `.tmp/sin_leads_[date].json`

### Step 3: Deduplication
- Check against existing Leads DB (Company + City match)

### Step 4: Write to Notion Leads DB
- `Brand` → "Sheet It Now"
- `Lead Source` → "Google Maps Scrape"
- `Status` → "New"
- `Industry` → "Accounting"

### Step 5: Trigger Enrichment (D-ALL-01)

### Step 6: Log Results

## Outputs
- 100–200 accounting firm leads per week
- Feeds into D-ALL-01 enrichment → D-SIN-06 email outreach

## Cost
- ~$2–4/week for Apify

## Autoresearch Metrics
- **Primary:** ICP match rate
- **Secondary:** Leads per run, duplicate rate

## Dependencies
- `APIFY_API_TOKEN` in .env
- `NOTION_API_KEY` in .env
