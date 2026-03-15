# D-NCL-07: NCL Bilingual Cold Outreach Pipeline

## Goal
Take enriched No Code Lab leads and run them through a 3-email cold outreach sequence via Instantly. Detect language preference (EN vs ES) from lead signals and send in the appropriate language. Configure auto-replies for incoming responses.

## Trigger
**Event-driven:** Fires when leads with `Brand = No Code Lab` reach `Status = Enriched` in the Leads DB. Batches daily at 8:00 AM ET.

## Inputs
- Leads DB entries: Brand = "No Code Lab", Status = "Enriched", Email exists
- NCL Knowledge Base document (Notion Brand State Doc)
- NCL Email Templates (3 emails × 2 languages)

## Process

### Step 1: Read Enriched NCL Leads
- Query Leads DB: Brand = NCL, Status = Enriched, Email exists
- Batch: up to 50 leads per daily run
- Script: `execution/notion_client.py`

### Step 2: Language Detection
- Check `City`/`State` for LATAM indicators
- Check company name for Spanish-language signals
- Check website language if URL available
- Default: English

### Step 3: Name Casualization
- Script: `execution/casualize_first_names_batch.py`
- Handles both EN and ES names

### Step 4: Generate Personalized Icebreakers
- Claude generates 1-line icebreaker per lead in appropriate language
- References their industry/company specifics + AI implementation angle

### Step 5: Create Instantly Campaign
- Script: `execution/instantly_create_campaigns.py`
- Separate EN and ES campaigns
- 3-email sequence:
  - **Email 1 (Day 0):** Pain point + free guide offer
  - **Email 2 (Day 3):** Specific AI win story + guide link
  - **Email 3 (Day 5):** Direct ask for walkthrough + calendar/guide link

### Step 6: Update Lead Status
- Each lead: `Status` → "Contacted"
- Log campaign ID in Notes

### Step 7: Configure Auto-Reply Webhook
- NCL knowledge base loaded in Instantly autoreply sheet
- Bilingual response capability
- Webhook: Modal function (D-NCL-09)

### Step 8: Log to Outreach Campaigns DB
- Create entry with campaign name, brand, type, platform, emails sent count

## Outputs
- Active Instantly campaign with 3-email sequences
- Leads updated to "Contacted" in Leads DB
- Campaign entry in Outreach Campaigns DB
- Auto-reply webhook ready

## Downstream
- Lead replies → D-NCL-09 (Email Auto-Replier)
- Lead clicks guide link → Status → "Replied"
- Alfredo reviews positive replies → manual "Qualified" or "Opportunity"

## Edge Cases
- **No email found:** Skip lead, leave at "Enriched"
- **Instantly daily limit:** Queue for next day
- **Bounce detected:** Enrichment Status → "Failed", remove from campaign
- **Unsubscribe reply:** Lead status → "Disqualified"

## Cost
- ~$0.09/lead for full 3-email sequence
- 50 leads/day × 30 days = ~$135/month

## Autoresearch Metrics
- **Primary:** Reply rate (target >5%)
- **Secondary:** Open rate (>40%), positive reply rate (>2%), bounce rate (<5%)

## Dependencies
- `INSTANTLY_API_KEY` in .env
- `ANTHROPIC_API_KEY` in .env
- `NOTION_API_KEY` in .env
