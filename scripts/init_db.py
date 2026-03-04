#!/usr/bin/env python3
"""Initialize the SQLite database with schema and seed data."""

import json
import sys
from pathlib import Path

# Allow running from repo root
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.database import DB_PATH, db_session

SCHEMA_PATH = Path(__file__).parent.parent / "config" / "schema.sql"
SEED_PATH = Path(__file__).parent.parent / "data" / "seed_data.json"


def init_schema(conn):
    schema = SCHEMA_PATH.read_text()
    conn.executescript(schema)
    print(f"[ok] Schema applied → {DB_PATH}")


def seed_funds(conn, funds: list[dict]) -> dict[str, int]:
    """Insert funds and return {name: id} mapping."""
    mapping = {}
    for f in funds:
        cur = conn.execute(
            """
            INSERT INTO funds (name, cik, manager, source_url)
            VALUES (:name, :cik, :manager, :source_url)
            ON CONFLICT(name) DO UPDATE SET
                cik=excluded.cik,
                manager=excluded.manager,
                source_url=excluded.source_url
            RETURNING id
            """,
            f,
        )
        mapping[f["name"]] = cur.fetchone()[0]
    print(f"[ok] {len(funds)} funds seeded")
    return mapping


def seed_filings(conn, filings: list[dict], fund_map: dict[str, int]) -> dict[tuple, int]:
    """Insert filings and return {(fund_name, quarter): id} mapping."""
    mapping = {}
    for filing in filings:
        fund_id = fund_map[filing["fund_name"]]
        cur = conn.execute(
            """
            INSERT INTO filings (fund_id, quarter, period_date, filed_date, total_value, source)
            VALUES (:fund_id, :quarter, :period_date, :filed_date, :total_value, :source)
            ON CONFLICT(fund_id, quarter) DO UPDATE SET
                period_date=excluded.period_date,
                total_value=excluded.total_value
            RETURNING id
            """,
            {**filing, "fund_id": fund_id},
        )
        mapping[(filing["fund_name"], filing["quarter"])] = cur.fetchone()[0]
    print(f"[ok] {len(filings)} filings seeded")
    return mapping


def seed_positions(conn, positions: list[dict], filing_map: dict[tuple, int]):
    for pos in positions:
        filing_id = filing_map[(pos["fund_name"], pos["quarter"])]
        conn.execute(
            """
            INSERT INTO positions
                (filing_id, ticker, company_name, shares, value_usd,
                 pct_portfolio, change_type, change_pct, prev_shares)
            VALUES
                (:filing_id, :ticker, :company_name, :shares, :value_usd,
                 :pct_portfolio, :change_type, :change_pct, :prev_shares)
            """,
            {**pos, "filing_id": filing_id},
        )
    print(f"[ok] {len(positions)} positions seeded")


def main():
    seed = json.loads(SEED_PATH.read_text())
    with db_session() as conn:
        init_schema(conn)
        fund_map = seed_funds(conn, seed["funds"])
        filing_map = seed_filings(conn, seed["filings"], fund_map)
        seed_positions(conn, seed["positions"], filing_map)

    print(f"\n Database ready at: {DB_PATH}")
    print("Run: tracker funds list")


if __name__ == "__main__":
    main()
