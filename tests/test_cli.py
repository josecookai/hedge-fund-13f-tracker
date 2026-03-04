"""Basic CLI smoke tests."""

import os
import pytest
from pathlib import Path
from click.testing import CliRunner

from src.cli.main import cli


SCHEMA_PATH = Path(__file__).parent.parent / "config" / "schema.sql"


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def empty_db(tmp_path, monkeypatch):
    """Provide a fresh empty (schema-initialized) test DB."""
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DB_PATH", str(db_path))
    # Apply schema so tables exist
    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA_PATH.read_text())
    conn.commit()
    conn.close()
    return db_path


def test_cli_help(runner):
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Monitor hedge fund" in result.output


def test_funds_list_empty(runner, empty_db):
    result = runner.invoke(cli, ["funds", "list"])
    assert result.exit_code == 0
    assert "No funds found" in result.output


def test_holdings_show_missing(runner, empty_db):
    result = runner.invoke(cli, ["holdings", "show", "NonExistentFund"])
    assert result.exit_code == 1
