---
name: hedge-fund-13f-tracker
description: >
  Monitor institutional investor holdings via SEC 13F filings. Track hedge fund
  positions, detect changes, and identify smart money consensus.
  
  Use when: (1) Tracking hedge fund portfolio changes, (2) Identifying institutional
  consensus on stocks, (3) Analyzing quarter-over-quarter position changes, 
  (4) Following "smart money" investment trends, (5) Comparing hedge fund strategies.
---

# 🐋 Hedge Fund 13F Tracker - OpenClaw Skill

> Monitor institutional "smart money" via SEC 13F filings

## 🎯 Natural Language Commands

### List Tracked Funds
```
"Show me tracked hedge funds"
"List all 13F filers"
"Which hedge funds are you monitoring?"
```

### View Holdings
```
"What does Atreides Management hold?"
"Show me NVDA holders"
"Which funds own META?"
"Display Monolith Management Q4 2024 holdings"
```

### Compare Quarters
```
"What changed for Atreides from Q3 to Q4 2024?"
"Compare Atreides Management Q3 vs Q4"
"Show me position changes for Situational Awareness"
```

### Consensus Analysis
```
"Which funds hold NVDA?"
"Show consensus on TSLA"
"What are the top consensus holdings?"
"Institutional heatmap for tech stocks"
```

### Alerts & Changes
```
"Alert me when new 13F filings appear"
"Show me recent position changes"
"What positions were added this quarter?"
"Which stocks were sold out?"
```

## 🛠️ Available Tools

### CLI Commands
- `hf-tracker list-funds` - List all tracked funds
- `hf-tracker holdings --fund <fund>` - Show fund holdings
- `hf-tracker compare --fund <fund> -q1 <Q1> -q2 <Q2>` - Compare quarters
- `hf-tracker consensus --ticker <TICKER>` - Cross-fund analysis

### Python API
```python
from scripts.alert_engine import AlertEngine
from scripts.ingest_filing import FilingIngester

# Detect changes
engine = AlertEngine()
changes = engine.detect_changes("atreides-management", "2024-Q3", "2024-Q4")

# Import filing
ingester = FilingIngester()
ingester.import_from_csv("data.csv", "fund-id", "2024-Q4")
```

### Web Dashboard
```bash
python scripts/dashboard.py
# http://localhost:8000
```

## 📊 Supported Funds

| Fund | CIK | AUM | Strategy |
|------|-----|-----|----------|
| Atreides Management | 0001736297 | $2.0B | Tech/Growth |
| Situational Awareness | 0002045724 | $5.5B | Macro/Event |
| Monolith Management | 0001652044 | $210M | Concentrated |

## 🔧 Configuration

### Environment Variables
```bash
export TELEGRAM_BOT_TOKEN=your_token    # For bot alerts
export RESEND_API_KEY=your_key          # For email reports
export REPORT_EMAIL=you@example.com     # Report recipient
```

### Database
- **Default**: `data/tracker.db` (SQLite)
- **Schema**: Auto-created on init
- **Backup**: Copy `.db` file

## 🚀 Quick Start

```bash
# 1. Clone and setup
git clone https://github.com/josecookai/hedge-fund-13f-tracker.git
cd hedge-fund-13f-tracker
pip install -r requirements.txt

# 2. Initialize database
python scripts/init_db.py --force

# 3. Use via CLI
./scripts/hf-tracker list-funds
./scripts/hf-tracker holdings --fund atreides-management

# 4. Or start web dashboard
python scripts/dashboard.py
```

## 📚 Data Sources

- **SEC EDGAR**: Official 13F filings
- **WhaleWisdom**: Aggregated fund data
- **HoldingsChannel**: Alternative source

## ⚠️ Limitations

- 13F only shows long positions >$100M
- 45-day delay after quarter-end
- No options/shorts included
- US equities only

## 🔗 Repository

https://github.com/josecookai/hedge-fund-13f-tracker
