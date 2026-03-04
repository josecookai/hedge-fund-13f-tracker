# 🐋 Hedge Fund 13F Tracker - Product Specification

> Monitor institutional investor holdings via SEC 13F filings - Track smart money moves like WhaleWisdom

**Version**: 1.0.0  
**Date**: 2026-03-04  
**Status**: Product Spec Complete

---

## 📋 Executive Summary

### Problem
- 13F filings are quarterly treasure troves of institutional investment data
- Hard to track multiple hedge funds across different sources (WhaleWisdom, HoldingsChannel, SEC EDGAR)
- No unified view of "smart money" consensus and divergences
- Delayed discovery of position changes (up to 45 days after quarter-end)

### Solution
Unified hedge fund 13F tracking system that:
- Aggregates 13F data from multiple sources
- Tracks position changes quarter-over-quarter
- Alerts on significant position modifications
- Shows consensus/divergence across funds

### Target Users
- Retail investors following "smart money"
- Financial analysts researching institutional trends
- Fund-of-funds managers tracking peers
- Financial journalists covering institutional moves

---

## 🎯 Core Features

### 1. Multi-Fund Tracking

**Supported Hedge Funds (Phase 1)**:
| Fund | Source | Strategy | AUM |
|------|--------|----------|-----|
| Atreides Management | WhaleWisdom | Long/Value | ~$2B |
| Monolith Management | HoldingsChannel | Long/Concentrated | ~$1B |
| WT Asset Management | WhaleWisdom | Multi-strategy | ~$500M |
| Situational Awareness LP | WhaleWisdom | Macro/Event | ~$300M |
| **+ User Add** | - | - | - |

**Fund Metadata**:
```json
{
  "id": "atreides-management",
  "name": "Atreides Management LP",
  "manager": "Gavin Baker",
  "strategy": "Long-term value, tech-focused",
  "aum": 2000000000,
  "sources": ["whalewisdom", "sec_edgar"],
  "13f_cik": "0001761945",
  "first_tracked_q": "2022-Q3"
}
```

### 2. Position Tracking

**Core Position Data**:
```json
{
  "fund_id": "atreides-management",
  "quarter": "2024-Q4",
  "filing_date": "2025-02-14",
  "positions": [
    {
      "ticker": "NVDA",
      "shares": 1500000,
      "value_usd": 450000000,
      "portfolio_pct": 22.5,
      "quarterly_change_pct": +15.2,
      "rank": 1,
      "activity": "added"  // new, added, reduced, sold
    }
  ]
}
```

**Key Metrics**:
- Portfolio weight (% of AUM)
- Quarterly share change (%)
- Ranking (top 10 positions)
- Activity status: NEW / ADDED / REDUCED / SOLD / UNCHANGED

### 3. Change Detection & Alerts

**Alert Triggers**:
- New position enters top 10
- Position size changes >20% QoQ
- Complete exit (sold out)
- New 13F filing published
- Consensus formation (3+ funds adding same stock)

**Alert Format**:
```
🚨 13F ALERT: Atreides Management

📊 NVDA - NEW TOP POSITION
• Shares: 1.5M (+15.2% QoQ)
• Value: $450M (22.5% of portfolio)
• Rank: #1 (was #3)
• Previous: 1.3M shares in Q3

🔗 View on WhaleWisdom: [link]
📄 SEC Filing: [link]
```

### 4. Consensus Analysis

**Smart Money Consensus**:
```
Top Consensus Holdings (3+ funds):
┌────────┬──────────┬──────────┬──────────┐
│ Ticker │ Funds    │ Avg Wt   │ Trend    │
├────────┼──────────┼──────────┼──────────┤
│ NVDA   │ 4/4      │ 18.2%    │ ↑↑↑      │
│ META   │ 3/4      │ 12.5%    │ ↑        │
│ AMZN   │ 3/4      │ 8.7%     │ →        │
│ TSLA   │ 2/4      │ 5.1%     │ ↓↓       │
└────────┴──────────┴──────────┴──────────┘
```

**Divergence Detection**:
- Fund A adding while Fund B reducing
- Contrarian positions worth investigating

### 5. Historical Analysis

**Quarter-over-Quarter Tracking**:
```
NVDA - Position History (Atreides):
┌─────────┬──────────┬──────────┬──────────┐
│ Quarter │ Shares   │ Value    │ Activity │
├─────────┼──────────┼──────────┼──────────┤
│ 2024-Q4 │ 1.5M     │ $450M    │ ADDED    │
│ 2024-Q3 │ 1.3M     │ $380M    │ ADDED    │
│ 2024-Q2 │ 1.0M     │ $280M    │ NEW      │
│ 2024-Q1 │ 0        │ $0       │ -        │
└─────────┴──────────┴──────────┴──────────┘
```

---

## 🔌 Data Sources

### Primary: WhaleWisdom
**URL**: https://whalewisdom.com

**Pros**:
- Clean, structured data
- Historical tracking
- Portfolio visualization
- Free tier available

**Cons**:
- Rate limited
- Requires API key for bulk access
- 13F data delayed by SEC filing delay

**API Endpoints** (conceptual):
```
GET /api/filer/{cik}/holdings
GET /api/filer/{cik}/history
GET /api/stock/{ticker}/holders
```

### Secondary: HoldingsChannel
**URL**: https://www.holdingschannel.com

**Pros**:
- Additional funds not on WhaleWisdom
- Top holdings summary

**Cons**:
- Less structured
- Requires scraping

### Tertiary: SEC EDGAR (Official)
**URL**: https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&type=13F

**Pros**:
- Official source
- Complete data
- Free

**Cons**:
- XML format
- Requires parsing
- Rate limited

---

## 🛠️ Technical Architecture

### Tech Stack
```
Backend: Python 3.10+
Data Storage: SQLite (dev) / PostgreSQL (prod)
API Layer: FastAPI
Scheduling: APScheduler / Cron
Notifications: Telegram Bot API
Web Scraping: Scrapy / Playwright
Data Parsing: BeautifulSoup, lxml
```

### Database Schema

```sql
-- Funds table
CREATE TABLE funds (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    manager TEXT,
    strategy TEXT,
    aum INTEGER,
    cik TEXT UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Filings table
CREATE TABLE filings (
    id TEXT PRIMARY KEY,
    fund_id TEXT REFERENCES funds(id),
    quarter TEXT NOT NULL,  -- "2024-Q4"
    filing_date DATE,
    report_date DATE,
    total_value INTEGER,
    position_count INTEGER
);

-- Positions table
CREATE TABLE positions (
    id TEXT PRIMARY KEY,
    filing_id TEXT REFERENCES filings(id),
    ticker TEXT NOT NULL,
    cusip TEXT,
    shares INTEGER,
    value INTEGER,
    portfolio_pct REAL,
    rank INTEGER
);

-- Position history for QoQ analysis
CREATE TABLE position_changes (
    id TEXT PRIMARY KEY,
    fund_id TEXT,
    ticker TEXT,
    quarter TEXT,
    previous_shares INTEGER,
    current_shares INTEGER,
    change_pct REAL,
    activity TEXT  -- NEW, ADDED, REDUCED, SOLD, UNCHANGED
);
```

---

## 📊 Output Formats

### 1. Daily Summary Report
```
🐋 Hedge Fund 13F Tracker - 2026-03-04
================================

📈 Latest Filings (Last 30 Days):
• Atreides Management - 2024-Q4 (Feb 14)
• Monolith Management - 2024-Q4 (Feb 13)
• WT Asset Management - 2024-Q4 (Feb 12)

🔥 Top Consensus Holdings:
1. NVDA - 4/4 funds, avg 18.2% weight
2. META - 3/4 funds, avg 12.5% weight  
3. AMZN - 3/4 funds, avg 8.7% weight

⚡ Notable Changes:
• Atreides: +15% NVDA, NEW position in TEM
• Monolith: -30% TSLA, EXITED PLTR
• WT Asset: +50% BTC ETF (IBIT)

🎯 New Positions (First Time):
• Atreides → TEM (Tempus AI) $45M
• Situational → COIN $28M

📉 Sold Out Completely:
• Monolith → PLTR (was $89M)
• WT Asset → RIVN (was $12M)
```

### 2. Individual Fund Report
```
📊 Atreides Management LP - 2024-Q4 13F
Manager: Gavin Baker | AUM: $2.0B
Filing Date: Feb 14, 2025

Top 10 Holdings:
┌────┬────────┬───────────┬────────────┬──────────┐
│Rank│ Ticker │ Shares    │ Value      │ QoQ Chg  │
├────┼────────┼───────────┼────────────┼──────────┤
│ 1  │ NVDA   │ 1,500,000 │ $450.0M    │ +15.2%   │
│ 2  │ META   │   800,000 │ $320.0M    │ +5.3%    │
│ 3  │ AMZN   │ 1,200,000 │ $210.0M    │ -2.1%    │
│ 4  │ TEM    │   500,000 │ $ 45.0M    │ NEW      │
│ 5  │ VST    │   300,000 │ $ 48.0M    │ +25.0%   │
└────┴────────┴───────────┴────────────┴──────────┘

Activity Summary:
• NEW positions: TEM, APP
• ADDED: NVDA (+200K), VST (+60K)
• REDUCED: AMZN (-25K)
• SOLD: PLTR, RIVN

Full filing: [SEC EDGAR link]
```

### 3. Stock-Specific Report
```
📈 NVDA - Institutional Ownership Analysis

Top Holders (by value):
┌──────────────────────┬───────────┬────────────┐
│ Fund                 │ Shares    │ Portfolio% │
├──────────────────────┼───────────┼────────────┤
│ Atreides Management  │ 1,500,000 │ 22.5%      │
│ Monolith Management  │   900,000 │ 18.2%      │
│ WT Asset Management  │   450,000 │ 15.1%      │
│ Situational Awareness│   280,000 │ 12.8%      │
└──────────────────────┴───────────┴────────────┘

Trend: ↑↑↑ (All 4 funds added or maintained in Q4)
Consensus: STRONG BULLISH
```

---

## 🚀 Development Phases

### Phase 1: MVP (Week 1-2)
**Goal**: Basic tracking for 4 funds, manual data entry or simple scraping

**Features**:
- [ ] Fund database setup
- [ ] Manual 13F data import (CSV/JSON)
- [ ] Position tracking & history
- [ ] Basic CLI report generation
- [ ] Telegram notifications

**Team**: @codex (data pipeline) + @claude-code (reporting)

### Phase 2: Automation (Week 3-4)
**Goal**: Automated data fetching, real alerts

**Features**:
- [ ] WhaleWisdom API integration
- [ ] SEC EDGAR parser
- [ ] Automatic change detection
- [ ] Alert system (new positions, significant changes)
- [ ] Web dashboard (basic)

**Team**: @codex (APIs) + @claude-code (alerts/dashboard)

### Phase 3: Scale (Month 2)
**Goal**: More funds, advanced analytics

**Features**:
- [ ] User-defined fund tracking
- [ ] Consensus scoring algorithm
- [ ] Historical backtesting
- [ ] Sector rotation tracking
- [ ] Mobile app (optional)

---

## ⚠️ Important Limitations

### 13F Limitations (Users Must Know)
1. **Only long positions >$100M** - No shorts, no options, no small positions
2. **Quarterly only** - 45 days after quarter-end delay
3. **Snapshot in time** - Position may have changed since filing
4. **No international** - US equities and ADRs only
5. **Group entities** - Some funds file under multiple entities

### Data Quality
- WhaleWisdom aggregates from SEC but may have parsing errors
- HoldingsChannel data may be incomplete
- Always verify critical data against SEC EDGAR

---

## 📈 Success Metrics

- [ ] Track 4+ hedge funds accurately
- [ ] Detect new 13F filings within 24 hours
- [ ] Alert on significant position changes (>20%)
- [ ] Position history accuracy >99%
- [ ] Report generation <30 seconds
- [ ] User can add custom funds

---

## 🔗 References

- SEC 13F FAQ: https://www.sec.gov/divisions/investment/13ffaq.htm
- WhaleWisdom: https://whalewisdom.com
- HoldingsChannel: https://www.holdingschannel.com
- Example Fund: https://whalewisdom.com/filer/atreides-management-lp

---

*Product Spec v1.0 - Smrti Lab*
