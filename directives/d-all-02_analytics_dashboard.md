# D-ALL-02: Analytics Dashboard Updater

## Goal
Pull metrics from all platforms (X/Twitter, LinkedIn, Instantly, product dashboards) for all 4 brands and write weekly entries to the Notion Metrics Dashboard DB. This powers the Monday morning review and provides the data layer for the autoresearch experiment loop.

## Trigger
**Scheduled:** Runs every Monday at 6:00 AM ET via Modal cron job.
Manual: `python execution/pull_all_metrics.py`

## Inputs
- X/Twitter API (if available) or public profile scraping
- Instantly API (campaign metrics)
- Notion Leads DB (lead counts by brand and status)
- Notion Content Library DB (content published counts)
- Notion Outreach Campaigns DB (campaign performance)
- Buffer API (scheduled content metrics)

## Process

### Step 1: Pull X/Twitter Metrics (per brand account)
For each brand's X account (SQS, AOQ, SIN, NCL):
- Followers count
- Impressions (last 7 days)
- Engagement rate (likes + retweets + replies / impressions)
- Top performing tweet of the week
- Script: `execution/pull_x_metrics.py`
- Fallback: If X API unavailable, scrape public profile for follower count

### Step 2: Pull Email Metrics (from Instantly)
For each active Instantly campaign:
- Emails sent (last 7 days)
- Open rate
- Reply rate
- Positive replies count
- Script: `execution/pull_instantly_metrics.py`

### Step 3: Pull Lead Pipeline Metrics (from Notion)
For each brand, query Leads DB:
- New leads added this week
- Leads enriched this week
- Leads contacted this week
- Leads replied this week
- Total leads by status
- Script: `execution/notion_client.py` (query with date filters)

### Step 4: Pull Content Metrics (from Notion)
For each brand, query Content Library DB:
- Content pieces published this week
- By platform (X, LinkedIn, Reddit, Blog)
- By pillar (Education, Proof, Engagement, CTA, BIP)

### Step 5: Calculate Derived Metrics
- Cost per lead (total Apify + AnyMailFinder spend / leads generated)
- Cost per reply (total Instantly spend / replies received)
- Content velocity (pieces published / target)
- Pipeline conversion rates (New → Enriched → Contacted → Replied → Qualified)

### Step 6: Write to Metrics Dashboard DB
For each brand × channel combination, create a Metrics DB entry:
- `Metric Entry` → "[Brand] - [Channel] - Week of [date]"
- `Brand` → brand name
- `Channel` → channel name
- `Period` → week start date
- Fill all applicable metric fields (Followers, Impressions, etc.)
- `Revenue` and `Cost` → from manual input or Stripe/billing data

### Step 7: Generate Monday Review Summary
- Create a summary page in Notion under the DOE Hub
- Highlights: wins, concerns, recommendations for the week
- Format for quick 30-min Monday review
- Script: `execution/generate_weekly_summary.py`

## Outputs
- Updated Metrics Dashboard DB entries for all brands and channels
- Monday Review Summary page in Notion
- Data available for all brand-filtered views (AOQ Metrics, SIN Metrics, NCL Metrics)

## Edge Cases
- **X API unavailable:** Use follower count from public profile, skip engagement metrics
- **Instantly API error:** Pull from last known data, flag as stale
- **No data for a brand:** Create entry with zeros, note "No activity this week"

## Cost
- API calls only, ~$0.00 (free tier for most APIs)
- Claude API for summary generation: ~$0.05/week

## Autoresearch Metrics
- **Primary:** Data completeness (% of expected metrics successfully pulled)
- **Secondary:** Execution time, accuracy of derived calculations

## Dependencies
- `NOTION_API_KEY` in .env
- `INSTANTLY_API_KEY` in .env
- `TWITTER_BEARER_TOKEN` in .env (optional)
- `BUFFER_ACCESS_TOKEN` in .env
