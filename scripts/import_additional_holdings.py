#!/usr/bin/env python3
"""
Import additional fund holdings from JSON seed file
"""
import sqlite3
import json
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / 'data' / 'tracker.db'
SEED_PATH = Path(__file__).parent.parent / 'data' / 'seed_additional_funds.json'

def import_additional_holdings():
    """Import holdings for additional funds"""
    
    print("📥 Importing Additional Fund Holdings\n")
    
    # Load seed data
    with open(SEED_PATH, 'r') as f:
        data = json.load(f)
    
    # Connect to database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Import filings
    filings_added = 0
    for filing in data['filings']:
        # Check if filing already exists
        cursor.execute('SELECT 1 FROM filings WHERE id = ?', (filing['id'],))
        if cursor.fetchone():
            continue
        
        cursor.execute('''
            INSERT INTO filings (id, fund_id, quarter, filing_date, report_date, total_value, position_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            filing['id'],
            filing['fund_id'],
            filing['quarter'],
            filing['filing_date'],
            filing['report_date'],
            filing['total_value'],
            filing['position_count']
        ))
        filings_added += 1
        print(f"  ✅ Added filing: {filing['fund_id']} {filing['quarter']}")
    
    # Import positions
    positions_added = 0
    for position in data['positions']:
        # Check if position already exists
        cursor.execute('SELECT 1 FROM positions WHERE id = ?', (position['id'],))
        if cursor.fetchone():
            continue
        
        cursor.execute('''
            INSERT INTO positions (id, filing_id, ticker, cusip, company_name, shares, value, portfolio_pct, rank)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            position['id'],
            position['filing_id'],
            position['ticker'],
            position.get('cusip'),
            position.get('company_name'),
            position['shares'],
            position['value'],
            position['portfolio_pct'],
            position['rank']
        ))
        positions_added += 1
    
    conn.commit()
    conn.close()
    
    print(f"\n=== Summary ===")
    print(f"Filings added: {filings_added}")
    print(f"Positions added: {positions_added}")
    print(f"\n✅ Import complete!")

if __name__ == '__main__':
    import_additional_holdings()
