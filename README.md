---
name: hedge-fund-13f-tracker
description: >
  Monitor institutional investor holdings via SEC 13F filings. Track hedge fund
  positions, detect changes, and identify smart money consensus. Supports
  WhaleWisdom integration, SEC EDGAR parsing, and automated alerts.
  
  Use when: (1) Tracking hedge fund portfolio changes, (2) Identifying institutional
  consensus on stocks, (3) Monitoring 13F filings for new positions, (4) Analyzing
  quarter-over-quarter position changes, (5) Following "smart money" investment trends.
---

# Hedge Fund 13F Tracker

> Monitor institutional investor holdings via SEC 13F filings - Track smart money moves

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![OpenClaw](https://img.shields.io/badge/OpenClaw-Skill-blue)](https://clawd.bot)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-Skill-green)](https://claude.ai)

## 📋 Overview

Track hedge fund 13F filings to monitor institutional "smart money" positions:
- **Multi-fund tracking**: Atreides, Monolith, WT Asset, Situational Awareness
- **Change detection**: New positions, additions, reductions, exits
- **Consensus analysis**: See what multiple funds agree on
- **Automated alerts**: Get notified of significant position changes
- **Quarterly updates**: Track Q-over-Q portfolio evolution

**Data Sources**: SEC EDGAR, WhaleWisdom, HoldingsChannel

## ✨ Features

- 📊 **Multi-Fund Tracking**: Monitor 4+ hedge funds simultaneously
- 🔔 **Change Alerts**: NEW / ADDED / REDUCED / SOLD detection
- 🎯 **Consensus View**: Cross-fund position analysis
- 📈 **Historical QoQ**: Quarter-over-quarter position tracking
- 🐋 **WhaleWisdom Integration**: Automated data fetching
- 📱 **Telegram Alerts**: Real-time position change notifications
- 🌐 **Web Dashboard**: Visual portfolio browser

## 🚀 Quick Start

```bash
# Clone repository
git clone https://github.com/josecookai/hedge-fund-13f-tracker.git
cd hedge-fund-13f-tracker

# Install dependencies
pip install -r requirements.txt

# Setup database
python scripts/init_db.py --force

# Use CLI to explore data
./scripts/hf-tracker list-funds
./scripts/hf-tracker holdings --fund atreides-management --quarter 2024-Q4
./scripts/hf-tracker compare --fund atreides-management -q1 2024-Q3 -q2 2024-Q4
./scripts/hf-tracker consensus --ticker NVDA
```

## 🤖 Skill Integration

### OpenClaw Skill

```bash
# Install
clawdhub install hedge-fund-13f-tracker

# Use natural language
clawd "Show me Atreides Management holdings"
clawd "What changed in Q4 2024?"
clawd "Which funds hold NVDA?"
clawd "Alert me when new 13F filings appear"
```

### Claude Code Skill

```bash
# Analysis commands
/claude "Analyze consensus on NVDA across all funds"
/claude "Compare Monolith vs Atreides tech holdings"
/claude "Generate Q4 2024 sector rotation report"

# Development
/claude "Implement SEC EDGAR parser"
/claude "Build consensus scoring algorithm"
```

## 📁 Project Structure

```
hedge-fund-13f-tracker/
├── PRODUCT_SPEC.md         # Detailed product specification
├── ROADMAP.md              # Development roadmap with task assignments
├── README.md               # This file
├── config/
│   ├── database.py         # Database configuration
│   └── funds.json          # Fund metadata
├── data/
│   ├── schema.sql          # Database schema
│   └── seed_data.json      # Initial fund data
├── scripts/
│   ├── hf-tracker          # Main CLI entry
│   ├── init_db.py          # Database initialization
│   ├── ingest_filing.py    # 13F data ingestion
│   ├── alert_engine.py     # Change detection & alerts
│   ├── consensus.py        # Cross-fund analysis
│   └── data_sources/       # Data source integrations
│       ├── sec_edgar.py
│       ├── whalewisdom.py
│       └── holdingschannel.py
├── dashboard/              # Web dashboard
│   ├── app.py              # FastAPI backend
│   └── templates/          # HTML templates
└── tests/                  # Unit & integration tests
```

## 📊 Supported Funds (Phase 1)

| Fund | Manager | Strategy | Source |
|------|---------|----------|--------|
| **Atreides Management** | Gavin Baker | Long-term value, tech | WhaleWisdom |
| **Monolith Management** | - | Long, concentrated | HoldingsChannel |
| **WT Asset Management** | - | Multi-strategy | WhaleWisdom |
| **Situational Awareness LP** | - | Macro/Event-driven | WhaleWisdom |

*Add custom funds via `hf-tracker add-fund`*

## 🛠️ CLI Commands

### Available Commands

```bash
# List all tracked hedge funds
./scripts/hf-tracker list-funds

# Show fund holdings (default: latest quarter)
./scripts/hf-tracker holdings --fund atreides-management
./scripts/hf-tracker holdings --fund atreides-management --quarter 2024-Q4 --top 10

# Compare quarters for change detection
./scripts/hf-tracker compare --fund atreides-management -q1 2024-Q3 -q2 2024-Q4

# Show consensus across all funds for a ticker
./scripts/hf-tracker consensus --ticker NVDA
./scripts/hf-tracker consensus --ticker META
```

### Data Import Commands

```bash
# Import from SEC EDGAR (requires CIK in database)
python scripts/ingest_filing.py --fund atreides-management --quarter 2024-Q4 --source sec

# Import from CSV
python scripts/ingest_filing.py --fund monolith-management --quarter 2024-Q4 --source csv --file data/sample.csv

# Import from JSON
python scripts/ingest_filing.py --fund situational-awareness --quarter 2024-Q4 --source json --file data/sample.json
```

## 📈 Sample Output

### List Funds
```
🐋 Tracked Hedge Funds

================================================================================
Fund                      Manager                       AUM Quarter     Filings
--------------------------------------------------------------------------------
Situational Awareness LP  Unknown                     $5.5B 2024-Q4           1
Atreides Management LP    Gavin Baker                 $2.0B 2024-Q4           2
WT Asset Management Ltd   Unknown                     $500M N/A               0
Monolith Management Ltd   Xi Cao, Timothy Wang        $210M 2024-Q4           1
================================================================================
Total: 4 funds
```

### Compare Quarters
```
📈 Atreides Management LP
Comparing 2024-Q3 → 2024-Q4

🆕 NEW POSITIONS:
   VST    Vistra Corp                      $   48.0M (2.6%)
   TEM    Tempus AI Inc                    $   45.0M (2.4%)
   APP    AppLovin Corporation             $   42.0M (2.3%)

❌ SOLD OUT:
   GOOGL  Alphabet Inc Class A             (was $  420.0M)
   PLTR   Palantir Technologies            (was $   75.0M)

📈 INCREASED:
   NVDA   +  15.4%  1300K → 1500K shares
   AVGO   +  14.3%  70K → 80K shares

📉 DECREASED:
   AMZN      -2.0%  1225K → 1200K shares

Summary: 5 new, 2 sold, 4 increased, 1 decreased, 0 unchanged
```

## 🗺️ Development Roadmap

See [ROADMAP.md](ROADMAP.md) for detailed sprint planning and task assignments.

### Phase 1: MVP (Week 1)
- Database setup & 4 funds tracked
- CLI report generation
- Manual data ingestion

### Phase 2: Automation (Week 2)
- WhaleWisdom API integration
- Change detection & alerts
- Web dashboard

### Phase 3: Analytics (Week 3)
- Consensus analysis
- Divergence detection
- Telegram bot

## 🤝 Contributing

**Dual Skill Development**:
- **@kimi-code**: Data pipelines, API integration, database
- **@claude-code**: Analytics, reporting, dashboard, alerts

See ROADMAP.md for task assignments.

## ⚠️ Important Limitations

**13F Filing Limitations**:
- Only long positions >$100M (no shorts, no options)
- Quarterly only (45-day delay after quarter-end)
- Snapshot in time (position may have changed)
- US equities only

**Data Quality**:
- Cross-reference critical data against SEC EDGAR
- WhaleWisdom/HoldingsChannel may have parsing errors

## 📚 References

- **SEC 13F FAQ**: https://www.sec.gov/divisions/investment/13ffaq.htm
- **WhaleWisdom**: https://whalewisdom.com
- **Example - Atreides**: https://whalewisdom.com/filer/atreides-management-lp
- **Product Spec**: [PRODUCT_SPEC.md](PRODUCT_SPEC.md)

## 📄 License

MIT License - see LICENSE file

---

*Track smart money. Follow the whales. 🐋*
