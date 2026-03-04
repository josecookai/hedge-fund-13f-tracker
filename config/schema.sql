-- Hedge Fund 13F Tracker - Database Schema
-- Sprint 1 Day 1-2

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- Tracked hedge funds
CREATE TABLE IF NOT EXISTS funds (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL UNIQUE,
    cik         TEXT    UNIQUE,          -- SEC CIK identifier
    manager     TEXT,                    -- Fund manager name
    source_url  TEXT,                    -- Primary data source URL
    active      INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- 13F filing records (one per fund per quarter)
CREATE TABLE IF NOT EXISTS filings (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    fund_id      INTEGER NOT NULL REFERENCES funds(id) ON DELETE CASCADE,
    quarter      TEXT    NOT NULL,       -- e.g. "2024Q4"
    period_date  TEXT    NOT NULL,       -- e.g. "2024-12-31"
    filed_date   TEXT,                   -- Date SEC received filing
    total_value  REAL,                   -- Total portfolio value (USD millions)
    source       TEXT    NOT NULL DEFAULT 'manual',  -- manual | edgar | whalewisdom
    raw_url      TEXT,
    created_at   TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE(fund_id, quarter)
);

-- Individual stock positions per filing
CREATE TABLE IF NOT EXISTS positions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    filing_id       INTEGER NOT NULL REFERENCES filings(id) ON DELETE CASCADE,
    ticker          TEXT    NOT NULL,
    cusip           TEXT,
    company_name    TEXT    NOT NULL,
    shares          INTEGER NOT NULL,
    value_usd       REAL    NOT NULL,    -- USD thousands (as reported in 13F)
    pct_portfolio   REAL,               -- % of total portfolio
    change_type     TEXT    DEFAULT NULL CHECK(change_type IN ('NEW','ADDED','REDUCED','SOLD', NULL)),
    change_pct      REAL    DEFAULT NULL,
    prev_shares     INTEGER DEFAULT NULL,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_positions_ticker   ON positions(ticker);
CREATE INDEX IF NOT EXISTS idx_positions_filing   ON positions(filing_id);
CREATE INDEX IF NOT EXISTS idx_filings_fund       ON filings(fund_id);
CREATE INDEX IF NOT EXISTS idx_filings_quarter    ON filings(quarter);
