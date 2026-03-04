# 🗺️ Hedge Fund 13F Tracker - Development Roadmap

**Project**: hedge-fund-13f-tracker  
**Version**: 1.0.0  
**Date**: 2026-03-04  
**Repos**: https://github.com/josecookai/hedge-fund-13f-tracker

---

## 👥 Development Team

| Developer | Specialization | Tasks |
|-----------|---------------|-------|
| **@kimi-code** (Kimi) | Data pipelines, APIs, scraping | Database, data ingestion, SEC/WhaleWisdom integration |
| **@claude-code** (Claude) | Analytics, reporting, architecture | Change detection, alerts, dashboard, consensus algorithms |

---

## 📅 Sprint Schedule

### Sprint 1: Foundation (Day 1-7) - Week 1

#### Day 1-2: Project Setup & Database ✅ COMPLETE
**Assigned**: @kimi-code

**Tasks**:
- [x] Initialize GitHub repo with proper structure
- [x] Create database schema (SQLite for MVP)
- [x] Set up funds table with 4 initial funds:
  - Atreides Management (CIK: 0001761945)
  - Monolith Management
  - WT Asset Management  
  - Situational Awareness LP
- [x] Create filings and positions tables
- [x] Seed database with manual Q4 2024 data

**Status**: COMPLETE - Database initialized with 4 funds, 1 filing, 10 positions

**Deliverables**:
```
hedge-fund-13f-tracker/
├── config/
│   ├── database.py
│   └── schema.sql
├── data/
│   └── seed_data.json
└── scripts/
    └── init_db.py
```

**Definition of Done**:
```bash
python scripts/init_db.py
# Database created with 4 funds, sample Q4 2024 data
sqlite3 data/tracker.db ".tables"  # shows funds, filings, positions
```

---

#### Day 3-4: Data Ingestion Pipeline ✅ COMPLETE
**Assigned**: @kimi-code

**Tasks**:
- [x] Create SEC EDGAR 13F parser (XML to JSON)
- [x] Implement SEC EDGAR fetcher
- [ ] Implement WhaleWisdom scraper (backup source) - Moved to Sprint 2
- [x] Build CSV/JSON import system for manual data
- [x] Create `ingest_filing.py` script

**Files Created**:
- `scripts/parse_13f.py` - 13F XML/TXT parser
- `scripts/fetch_sec.py` - SEC EDGAR fetcher with rate limiting
- `scripts/ingest_filing.py` - Unified import system (SEC, CSV, JSON)
- `data/sample_import.csv` - Sample import file

**Usage**:
```bash
# Import from CSV
python scripts/ingest_filing.py --fund atreides-management --quarter 2024-Q4 --source csv --file data/sample_import.csv

# Import from SEC EDGAR
python scripts/ingest_filing.py --fund atreides-management --quarter 2024-Q4 --source sec
```

**Status**: COMPLETE - CSV/JSON/SEC import working

---

#### Day 5-7: CLI Core & Basic Reports ✅ COMPLETE (by @kimi-code)
**Assigned**: @claude-code (completed by @kimi-code)

**Tasks**:
- [x] Create CLI entry point `hf-tracker`
- [x] Build `list-funds` command
- [x] Build `holdings` command
- [x] Build `compare` command (QoQ change detection)
- [x] Build `consensus` command (cross-fund analysis)
- [x] Position change detection logic (NEW, SOLD, ADDED, REDUCED)
- [x] Basic text output formatting

**Files Created**:
- `scripts/hf-tracker` - Main CLI executable
- Comprehensive CLI with 4 commands
- Real-time change detection between quarters

**CLI Commands** (All Working):
```bash
./scripts/hf-tracker list-funds                          # List all funds
./scripts/hf-tracker holdings --fund atreides-management # Show holdings
./scripts/hf-tracker compare --fund atreides -q1 2024-Q3 -q2 2024-Q4
./scripts/hf-tracker consensus --ticker NVDA             # Cross-fund view
```

**Status**: COMPLETE - CLI fully functional with change detection

---

### Sprint 2: Automation (Day 8-14) - Week 2

#### Day 8-10: Change Detection & Alerts
**Assigned**: @claude-code

**Tasks**:
- [ ] Implement change detection algorithm
- [ ] Define alert rules:
  - NEW position (was 0, now >0)
  - ADDED (>20% increase)
  - REDUCED (>20% decrease)
  - SOLD (was >0, now 0)
- [ ] Create alert notification formatter
- [ ] Telegram integration
- [ ] Alert history logging

**Alert Logic**:
```python
# scripts/alert_engine.py
def detect_changes(fund_id: str, new_quarter: str, old_quarter: str) -> list:
    """Returns list of position changes"""
    
def should_alert(change: dict) -> bool:
    """Check if change meets alert threshold"""
    # NEW: always alert
    # ADDED: >20% increase
    # REDUCED: >20% decrease
    # SOLD: always alert (if was top 20)
```

**Deliverables**:
- `alert_engine.py` with detection logic
- Telegram notifications working
- Alert configuration file

---

#### Day 11-12: Web Dashboard (MVP)
**Assigned**: @claude-code

**Tasks**:
- [ ] Set up FastAPI backend
- [ ] Create API endpoints:
  - GET /api/funds
  - GET /api/funds/{id}/holdings
  - GET /api/funds/{id}/changes
  - GET /api/consensus
- [ ] Basic HTML dashboard (no JS framework)
- [ ] Position tables with sorting
- [ ] Simple charts (Chart.js)

**Dashboard Pages**:
- `/` - Fund overview list
- `/fund/{id}` - Individual fund holdings
- `/consensus` - Cross-fund consensus view
- `/alerts` - Recent alert history

**Deliverables**:
- Running web server on localhost:8000
- 3 dashboard pages functional
- API returns JSON data

---

#### Day 13-14: WhaleWisdom API Integration
**Assigned**: @kimi-code

**Tasks**:
- [ ] Research WhaleWisdom API (or scraping if no API)
- [ ] Implement data fetcher
- [ ] Handle rate limiting
- [ ] Error handling & retries
- [ ] Data validation against SEC source

**Implementation**:
```python
# scripts/data_sources/whalewisdom.py
class WhaleWisdomSource:
    def fetch_holdings(self, fund_cik: str, quarter: str) -> list:
        """Fetch holdings from WhaleWisdom"""
        
    def validate_against_sec(self, ww_data: list, sec_data: list) -> bool:
        """Cross-validate data"""
```

**Deliverables**:
- Automated data fetching from WhaleWisdom
- Data validation logic
- Cron job setup for auto-ingestion

---

### Sprint 3: Polish & Scale (Day 15-21) - Week 3

#### Day 15-17: Consensus Analysis
**Assigned**: @claude-code

**Tasks**:
- [ ] Build consensus scoring algorithm
- [ ] Cross-fund position comparison
- [ ] Divergence detection (Fund A adds, Fund B reduces)
- [ ] Sector rotation tracking
- [ ] Top consensus holdings report

**Consensus Algorithm**:
```python
# scripts/consensus.py
def calculate_consensus(ticker: str, funds: list) -> dict:
    """
    Returns:
    - funds_holding: count
    - avg_weight: float
    - trend: ↑↑↑, ↑↑, ↑, →, ↓, ↓↓, ↓↓↓
    - consensus_score: 0-100
    """
```

---

#### Day 18-19: User Experience
**Assigned**: @kimi-code + @claude-code

**Tasks**:
- [ ] Telegram bot interactive commands
- [ ] Email report templates
- [ ] Add fund wizard (user input)
- [ ] Configuration management
- [ ] Documentation (README, SKILL.md)

**Telegram Bot Commands**:
```
/funds - List tracked funds
/holdings {fund} - Show top holdings  
/alerts - Recent alerts
/consensus {ticker} - Cross-fund view
/addfund - Add new fund to track
```

---

#### Day 20-21: Testing & Deployment
**Both developers**

**Tasks**:
- [ ] Unit tests for core functions
- [ ] Integration tests (end-to-end)
- [ ] Docker containerization
- [ ] Deployment documentation
- [ ] GitHub Actions CI/CD

---

## 📋 Task Assignments Summary

### @kimi-code Tasks (Data & Infrastructure)

| Sprint | Task | Days | Priority |
|--------|------|------|----------|
| 1 | Database setup & schema | 2 | P0 |
| 1 | Data ingestion pipeline | 2 | P0 |
| 2 | WhaleWisdom API integration | 2 | P1 |
| 3 | Add fund wizard & config | 1 | P2 |
| 3 | Testing & Docker | 1 | P1 |

**Key Skills**: Python, SQL, Web scraping, API integration

### @claude-code Tasks (Analytics & UX)

| Sprint | Task | Days | Priority |
|--------|------|------|----------|
| 1 | CLI core & basic reports | 3 | P0 |
| 2 | Change detection & alerts | 3 | P0 |
| 2 | Web dashboard | 2 | P1 |
| 3 | Consensus analysis | 2 | P2 |
| 3 | Telegram bot & UX | 2 | P1 |

**Key Skills**: Python, FastAPI, Frontend (HTML/JS), Data analysis

---

## 🎯 Daily Standup Format

**Recommended daily sync (async)**:

```
Day X Update - @developer

Yesterday:
- Completed: [task]
- Blockers: [if any]

Today:
- Working on: [task]
- ETA: [time]

Need help with:
- [question/issue]
```

---

## ✅ Definition of Done (v1.0)

- [ ] Track 4 hedge funds with accurate Q4 2024 data
- [ ] Detect and alert on position changes
- [ ] Generate fund-specific reports
- [ ] Show consensus across funds
- [ ] Telegram notifications working
- [ ] Web dashboard functional
- [ ] Documentation complete
- [ ] GitHub repo with CI/CD

---

## 🚀 Post-v1.0 Roadmap

### v1.1 (Month 2)
- [ ] Auto-detect new 13F filings
- [ ] More funds (10+)
- [ ] Email alerts
- [ ] Position size alerts (AUM %)

### v1.2 (Month 3)
- [ ] Historical backtesting
- [ ] Performance tracking
- [ ] Sector analysis
- [ ] Mobile app

### v2.0 (Future)
- [ ] ML-based consensus scoring
- [ ] Predictive alerts
- [ ] API for external access
- [ ] Paid tier with more funds

---

## 📚 Resources

**Data Sources**:
- SEC EDGAR: https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&type=13F
- WhaleWisdom: https://whalewisdom.com/filer/atreides-management-lp
- HoldingsChannel: https://www.holdingschannel.com

**Example 13F Filings**:
- Atreides Q4 2024: Search CIK 0001761945
- Monolith: Search holdingschannel.com

**Documentation**:
- PRODUCT_SPEC.md - Full product specification
- README.md - User documentation (to be created)
- SKILL.md - OpenClaw/Claude Code integration

---

## 💡 Development Tips

**For @kimi-code**:
- Start with hardcoded sample data, automate later
- Use SQLite for MVP, migrate to PostgreSQL in v1.1
- Test parsers against real SEC 13F XML files
- Rate limit all external requests

**For @claude-code**:
- Design for extensibility (easy to add new funds)
- Make alerts configurable (thresholds, channels)
- Dashboard first, polish later
- Use Jinja2 for report templates

---

Ready to start? Assign first tasks:

```
@kimi-code: Create database schema (Day 1-2)
@claude-code: Set up project structure & CLI skeleton (Day 1-2)
```

Let's build this! 🐋
