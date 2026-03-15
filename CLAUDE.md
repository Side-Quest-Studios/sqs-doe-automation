# SQS DOE Automation — Agent Instructions

> This file tells any Claude instance (Antigravity, Claude Code, Claude Projects, etc.) how to operate the Side Quest Studios automation system. Read this file first before doing anything.

You operate within a **4-layer architecture** based on Nick Saraev's DOE Framework + Karpathy's Autoresearch:

## The 4-Layer Architecture

**Layer 1: Directives (What to do)**
- Markdown SOPs in `directives/`
- Define goals, inputs, tools/scripts, outputs, edge cases, and metrics
- Written like instructions for a mid-level employee
- These are living documents that improve over time via the autoresearch loop

**Layer 2: Orchestration (Decision making)**
- This is YOU. Your job: intelligent routing.
- Read directives, call execution scripts in the right order, handle errors, update directives with learnings
- You don't do the heavy lifting yourself — you read `directives/d-aoq-04_gmaps_lead_scraper.md` and run `execution/scrape_google_maps.py`

**Layer 3: Execution (Doing the work)**
- Deterministic Python scripts in `execution/`
- Handle API calls, data processing, Notion database operations
- Environment variables and API keys stored in `.env`
- Reliable, testable, fast. Use scripts instead of manual work.

**Layer 4: Measurement (Continuous improvement)**
- Autoresearch-style experiment loop
- After every directive run, measure results against key metrics
- If metrics improved → keep the change, commit to git
- If metrics worsened → discard, revert to previous version
- Every experiment logged to Notion Experiment Log DB

**Why this works:** If you do everything yourself, errors compound. 90% accuracy per step = 59% success over 5 steps. Push execution into deterministic code. You focus on decision-making.

## Operating Principles

### 1. Check for existing tools first
Before writing any script, check `execution/` per your directive. Only create new scripts if none exist.

### 2. Self-anneal when things break
- Read error message and stack trace
- Fix the script and test again (unless it uses paid tokens/credits — check with user first)
- Update the directive with what you learned (API limits, timing, edge cases)
- The system gets stronger with every failure

### 3. Update directives as you learn
Directives are living documents. When you discover API constraints, better approaches, common errors, or timing expectations — update the directive. But don't overwrite directives without asking unless told to.

### 4. Always use Notion as the data layer
- **DO NOT** use Google Sheets for final deliverables
- All leads, campaigns, content, metrics, and experiments go to Notion databases via `execution/notion_client.py`
- `.tmp/` files are for intermediate processing only

### 5. Commit to git after successful changes
- After a directive run that produces good results: `git add . && git commit -m "description of what changed"`
- After a failed experiment: `git checkout -- .` to revert
- Never commit `.env`, `credentials.json`, or anything in `.tmp/`

## Brand Registry

SQS operates 4 brands. Always fetch the relevant Brand State Document from Notion before starting any brand-related task.

| Brand | Notion Brand State Doc | ICP |
|-------|----------------------|-----|
| Side Quest Studios | `notion.so/3221686ea89c81bb9027d0fa0d9fa6d3` | N/A (parent brand) |
| AddOnQuote | `notion.so/3221686ea89c8102b28cf098b29bbd23` | Roofing contractors, 2-20 employees, US |
| Sheet It Now | `notion.so/3221686ea89c812c93f8da57eae4e3d4` | Accounting firms, bookkeepers, CPAs, 2-20 employees, US |
| No Code Lab | `notion.so/3221686ea89c81699593ed33f52d1967` | Small business owners, 1-50 employees, US + LATAM |

## Notion Database Registry

All CRM and automation data lives in these Notion databases:

| Database | Notion ID | Purpose |
|----------|-----------|---------|
| Leads | `802e397dc5cc48d3b2ca0ac99cdd0bc7` | Master CRM — all scraped and manual leads |
| Outreach Campaigns | `b17603d0fe5b450cb6bf29883b8f36d8` | Email sequences, Reddit, LinkedIn, ad campaigns |
| Content Library | `5d01e5092f4645d596a88470720cdc35` | All content pieces across all platforms |
| Directives | `b216eec6274e46bda07a304cec3fffcf` | Registry of all DOE automation workflows |
| Experiment Log | `7ea6ca9fc83543f4b9a33500a4d3b17e` | Autoresearch experiment tracking |
| Metrics Dashboard | `02f98090fb374d95bce14b82d0d8e68c` | Weekly metrics across all brands and channels |
| Implementation Roadmap | `05729f396ea94f58abfa9f8cb2f9f5fa` | Setup tasks and progress tracking |

## Directive Naming Convention

Directives follow this pattern: `D-[BRAND]-[NUMBER]`
- `D-ALL-xx` = Shared across all brands
- `D-AOQ-xx` = AddOnQuote specific
- `D-SIN-xx` = Sheet It Now specific
- `D-NCL-xx` = No Code Lab specific
- `D-SQS-xx` = SQS Parent Brand specific

## File Organization

```
sqs-doe-automation/
├── CLAUDE.md              ← YOU ARE HERE. Read this first.
├── .env                   ← API keys (NEVER commit)
├── .env.example           ← Template showing required keys
├── .gitignore             ← Excludes .env, credentials, .tmp
├── requirements.txt       ← Python dependencies
├── directives/            ← All directive SOPs (markdown)
│   ├── d-all-01_lead_enrichment.md
│   ├── d-aoq-04_gmaps_lead_scraper.md
│   ├── d-ncl-07_cold_outreach.md
│   └── ...
├── execution/             ← Python scripts (deterministic tools)
│   ├── notion_client.py   ← Read/write Notion databases
│   ├── scrape_google_maps.py
│   ├── enrich_emails.py
│   ├── buffer_scheduler.py
│   └── ...
├── .tmp/                  ← Temporary files (gitignored)
└── results/               ← Experiment results (gitignored)
```

**Key principle:** Local files are only for processing. Deliverables live in Notion where the user can access them. Everything in `.tmp/` can be deleted and regenerated.

## Self-Annealing Loop

Errors are learning opportunities. When something breaks:
1. Fix the script
2. Test it
3. Update the directive with what you learned
4. Commit the improvement to git
5. System is now stronger

## Autoresearch Loop (Continuous Improvement)

After every directive run:
1. Measure the key metrics defined in the directive
2. Compare to previous best score
3. If improved → commit changes, update directive version, log to Experiment Log DB
4. If worse → revert changes, log as "discard" in Experiment Log DB
5. Propose next experiment variation
6. Repeat

## How to Start a Task

1. Read this file (CLAUDE.md) — you're doing this now
2. Identify which directive applies to the task
3. Read the directive from `directives/`
4. Fetch the relevant Brand State Document from Notion
5. Check that required API keys are in `.env`
6. Execute the scripts in order per the directive
7. Write results to Notion
8. Log metrics
9. Commit if successful

Be pragmatic. Be reliable. Self-anneal.
