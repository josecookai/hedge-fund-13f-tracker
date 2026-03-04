-- Hedge Fund 13F Tracker Database Schema
-- SQLite version for MVP

-- Funds table - tracked hedge funds
CREATE TABLE IF NOT EXISTS funds (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    manager TEXT,
    strategy TEXT,
    aum INTEGER,
    cik TEXT UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Filings table - 13F filings by quarter
CREATE TABLE IF NOT EXISTS filings (
    id TEXT PRIMARY KEY,
    fund_id TEXT REFERENCES funds(id) ON DELETE CASCADE,
    quarter TEXT NOT NULL,
    filing_date DATE,
    report_date DATE,
    total_value INTEGER,
    position_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Positions table - individual holdings
CREATE TABLE IF NOT EXISTS positions (
    id TEXT PRIMARY KEY,
    filing_id TEXT REFERENCES filings(id),
    ticker TEXT NOT NULL,
    cusip TEXT,
    company_name TEXT,
    shares INTEGER,
    value INTEGER,
    portfolio_pct REAL,
    rank INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Position changes table - QoQ analysis
CREATE TABLE IF NOT EXISTS position_changes (
    id TEXT PRIMARY KEY,
    fund_id TEXT REFERENCES funds(id),
    ticker TEXT,
    quarter TEXT,
    previous_shares INTEGER,
    current_shares INTEGER,
    change_pct REAL,
    activity TEXT,  -- NEW, ADDED, REDUCED, SOLD, UNCHANGED
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Alerts table - triggered alerts
CREATE TABLE IF NOT EXISTS alerts (
    id TEXT PRIMARY KEY,
    fund_id TEXT REFERENCES funds(id),
    ticker TEXT,
    alert_type TEXT,  -- NEW_POSITION, ADDED, REDUCED, SOLD, THRESHOLD
    message TEXT,
    sent BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_positions_filing ON positions(filing_id);
CREATE INDEX IF NOT EXISTS idx_positions_ticker ON positions(ticker);
CREATE INDEX IF NOT EXISTS idx_positions_ticker_filing ON positions(ticker, filing_id);
CREATE INDEX IF NOT EXISTS idx_changes_fund ON position_changes(fund_id, quarter);
CREATE INDEX IF NOT EXISTS idx_filings_fund_quarter ON filings(fund_id, quarter);
