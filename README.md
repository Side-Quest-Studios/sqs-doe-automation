# SQS DOE Automation

**Directives • Orchestration • Execution • Measurement**

Automated operations system for Side Quest Studios' 4 brands, built on Nick Saraev's DOE Framework + Karpathy's Autoresearch continuous improvement loop.

## What This Is

An AI-agent-operated automation system that handles lead generation, content creation, email outreach, analytics, and continuous self-improvement across:

- **AddOnQuote** — Profit optimization SaaS for roofing contractors
- **Sheet It Now** — PDF bank statement to Excel converter for accountants
- **No Code Lab** — Bilingual AI implementation playbooks for business owners
- **SQS (Parent)** — Building-in-public authority and cross-brand promotion

## Architecture

```
Layer 1: DIRECTIVES    → Markdown SOPs in directives/
Layer 2: ORCHESTRATION → Claude AI agent (reads directives, makes decisions)
Layer 3: EXECUTION     → Python scripts in execution/
Layer 4: MEASUREMENT   → Autoresearch loop (experiments, metrics, optimization)
```

All data flows through **Notion** (CRM, metrics, content library, experiment log).

## Quick Start

```bash
# 1. Clone this repo
git clone https://github.com/[your-username]/sqs-doe-automation.git
cd sqs-doe-automation

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy .env.example to .env and fill in your API keys
cp .env.example .env

# 4. Point your Claude instance at CLAUDE.md and start working
```

## How to Use

1. Open the repo in Antigravity (or any Claude-compatible IDE)
2. Claude reads `CLAUDE.md` for full system context
3. Tell Claude which directive to execute (e.g., "Run D-AOQ-04")
4. Claude reads the directive, runs the scripts, writes to Notion
5. Results are measured, logged, and the system improves over time

## Data Layer

All CRM and operational data lives in Notion databases. See `CLAUDE.md` for the complete database registry.

## License

Private — Side Quest Studios © 2026
