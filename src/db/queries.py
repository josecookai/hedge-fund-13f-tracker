"""Database query helpers used by CLI commands."""

from config.database import db_session


def list_funds() -> list[dict]:
    with db_session() as conn:
        rows = conn.execute(
            "SELECT id, name, cik, manager, active FROM funds ORDER BY name"
        ).fetchall()
    return [dict(r) for r in rows]


def get_fund_by_name(name: str) -> dict | None:
    with db_session() as conn:
        row = conn.execute(
            "SELECT * FROM funds WHERE lower(name) LIKE lower(?)", (f"%{name}%",)
        ).fetchone()
    return dict(row) if row else None


def list_holdings(fund_name: str, quarter: str | None = None) -> list[dict]:
    """Return positions for a fund, optionally filtered by quarter."""
    q = """
        SELECT p.ticker, p.company_name, p.shares, p.value_usd,
               p.pct_portfolio, p.change_type, p.change_pct,
               fi.quarter, f.name AS fund_name
        FROM positions p
        JOIN filings fi ON fi.id = p.filing_id
        JOIN funds f    ON f.id  = fi.fund_id
        WHERE lower(f.name) LIKE lower(?)
    """
    params: list = [f"%{fund_name}%"]
    if quarter:
        q += " AND fi.quarter = ?"
        params.append(quarter.upper())
    q += " ORDER BY p.pct_portfolio DESC"

    with db_session() as conn:
        rows = conn.execute(q, params).fetchall()
    return [dict(r) for r in rows]


def list_quarters(fund_name: str) -> list[str]:
    with db_session() as conn:
        rows = conn.execute(
            """
            SELECT fi.quarter FROM filings fi
            JOIN funds f ON f.id = fi.fund_id
            WHERE lower(f.name) LIKE lower(?)
            ORDER BY fi.quarter DESC
            """,
            (f"%{fund_name}%",),
        ).fetchall()
    return [r["quarter"] for r in rows]
