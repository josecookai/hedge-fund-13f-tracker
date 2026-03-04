"""Data models (dataclasses, no ORM)."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Fund:
    id: int
    name: str
    cik: Optional[str] = None
    manager: Optional[str] = None
    source_url: Optional[str] = None
    active: bool = True


@dataclass
class Filing:
    id: int
    fund_id: int
    quarter: str          # e.g. "2024Q4"
    period_date: str      # e.g. "2024-12-31"
    filed_date: Optional[str] = None
    total_value: Optional[float] = None
    source: str = "manual"


@dataclass
class Position:
    id: int
    filing_id: int
    ticker: str
    company_name: str
    shares: int
    value_usd: float
    cusip: Optional[str] = None
    pct_portfolio: Optional[float] = None
    change_type: Optional[str] = None   # NEW | ADDED | REDUCED | SOLD
    change_pct: Optional[float] = None
    prev_shares: Optional[int] = None
