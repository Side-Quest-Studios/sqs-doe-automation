# D-AOQ-04: AddOnQuote Google Maps Lead Scraper

## Goal
Scrape roofing contractors from Google Maps across target US metros every week. Filter for established businesses (10+ reviews, has website). Write to the Leads DB tagged as AddOnQuote. Automatically triggers the Lead Enrichment Pipeline (D-ALL-01).

## Trigger
**Scheduled:** Runs every Monday at 5:00 AM ET via Modal cron job.
Can also be triggered manually: `python execution/gmaps_lead_pipeline.py --brand addOnQuote`

## Inputs
- **Search query:** "roofing contractors"
- **Target metros (rotate weekly):**
  - Week 1: Austin TX, Dallas TX
  - Week 2: Phoenix AZ, Miami FL
  - Week 3: Atlanta GA, Houston TX
  - Week 4: Tampa FL, Charlotte NC
  - Week 5: Nashville TN, Denver CO
  - Then repeat cycle
- **Filters:** Min 10 Google reviews, must have website
- **Volume:** 50–125 leads per metro, 100–250 per weekly run

## Process

### Step 1: Test Scrape (Verification)
- Run `execution/scrape_google_maps.py` with `--limit 10` for the first metro
- Verify >80% of results are actual roofing contractors (not general contractors, suppliers, etc.)
- **Decision:** If <80% match, adjust search query and re-test. If >80%, proceed.

### Step 2: Full Scrape
- Run `execution/gmaps_lead_pipeline.py` with:
  - `--search "roofing contractors in [METRO]"` for each metro
  - `--limit 125`
  - `--workers 3`
- Uses Apify `compass/crawler-google-places` actor
- Output: `.tmp/aoq_leads_[date].json`

### Step 3: Deduplication
- Check each lead against existing Leads DB entries
- Match on: `Company` name + `City` (fuzzy match)
- Skip any lead already in the DB

### Step 4: Write to Notion Leads DB
- For each new lead, create entry in Leads DB:
  - `Lead Name` → Business name
  - `Company` → Business name
  - `Brand` → "AddOnQuote"
  - `Lead Source` → "Google Maps Scrape"
  - `Status` → "New"
  - `Website` → from Google Maps
  - `Phone` → from Google Maps
  - `City` → from address
  - `State` → from address
  - `Industry` → "Roofing"
  - `Enrichment Status` → "Pending"
- Script: `execution/notion_client.py`

### Step 5: Trigger Enrichment
- New leads with `Status = New` trigger D-ALL-01 (Lead Enrichment Pipeline)

### Step 6: Log Results
- Write to Metrics Dashboard DB and Experiment Log DB

## Outputs
- 100–250 new roofing contractor leads per week in Leads DB
- Metrics entry in Metrics Dashboard DB
- Feeds automatically into D-ALL-01 enrichment → D-AOQ-06 email outreach

## Edge Cases
- **Apify rate limit:** Reduce to 1 metro per run
- **Low match rate (<80%):** Try alternate queries: "roof repair", "roofing company"
- **All duplicates:** Expand to new metros not in rotation
- **API error:** Retry once. If persistent, alert via Slack.

## Cost
- ~$0.01–0.02 per lead × 250 leads/week = ~$2.50–5.00/week

## Autoresearch Metrics
- **Primary:** ICP match rate (% actual roofing contractors)
- **Secondary:** Leads per run, duplicate rate, cost per lead

## Dependencies
- `APIFY_API_TOKEN` in .env
- `NOTION_API_KEY` in .env
