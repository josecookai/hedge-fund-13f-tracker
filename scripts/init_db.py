#!/usr/bin/env python3
"""
Initialize Hedge Fund 13F Tracker database
Creates schema and seeds with sample data
"""
import sqlite3
import json
import os
from pathlib import Path

def init_database(db_path='data/tracker.db', schema_path='data/schema.sql', force=False):
    """Initialize database with schema"""
    
    # Ensure data directory exists
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    
    # Remove existing database for fresh start (only with --force)
    if os.path.exists(db_path):
        if force:
            print(f"Removing existing database: {db_path}")
            os.remove(db_path)
        else:
            print(f"Database already exists: {db_path}")
            print("Use --force to overwrite")
            return sqlite3.connect(db_path)
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Execute schema
    print(f"Loading schema from {schema_path}...")
    with open(schema_path, 'r') as f:
        schema = f.read()
    
    cursor.executescript(schema)
    conn.commit()
    print(f"✅ Database schema created: {db_path}")
    
    return conn

def seed_data(conn, seed_path='data/seed_data.json'):
    """Seed database with initial data"""
    
    cursor = conn.cursor()
    
    print(f"Loading seed data from {seed_path}...")
    with open(seed_path, 'r') as f:
        data = json.load(f)
    
    # Insert funds
    print(f"Inserting {len(data['funds'])} funds...")
    for fund in data['funds']:
        cursor.execute('''
            INSERT INTO funds (id, name, manager, strategy, aum, cik)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            fund['id'],
            fund['name'],
            fund.get('manager'),
            fund.get('strategy'),
            fund.get('aum'),
            fund.get('cik')
        ))
    
    # Insert filings
    print(f"Inserting {len(data['filings'])} filings...")
    for filing in data['filings']:
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
    
    # Insert positions
    print(f"Inserting {len(data['positions'])} positions...")
    for position in data['positions']:
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
    
    conn.commit()
    print("✅ Seed data inserted successfully")

def verify_database(conn):
    """Verify database contents"""
    
    cursor = conn.cursor()
    
    print("\n📊 Database Verification:")
    print("-" * 40)
    
    # Count funds
    cursor.execute('SELECT COUNT(*) FROM funds')
    fund_count = cursor.fetchone()[0]
    print(f"Funds: {fund_count}")
    
    # Count filings
    cursor.execute('SELECT COUNT(*) FROM filings')
    filing_count = cursor.fetchone()[0]
    print(f"Filings: {filing_count}")
    
    # Count positions
    cursor.execute('SELECT COUNT(*) FROM positions')
    position_count = cursor.fetchone()[0]
    print(f"Positions: {position_count}")
    
    # Show funds
    print("\n📈 Tracked Funds:")
    cursor.execute('SELECT id, name, manager FROM funds')
    for row in cursor.fetchall():
        print(f"  • {row[0]}: {row[1]} ({row[2]})")
    
    # Show top positions for Atreides
    print("\n🏆 Atreides Management - Top 5 Holdings (Q4 2024):")
    cursor.execute('''
        SELECT p.ticker, p.company_name, p.shares, p.value, p.portfolio_pct
        FROM positions p
        JOIN filings f ON p.filing_id = f.id
        WHERE f.fund_id = 'atreides-management'
        ORDER BY p.rank
        LIMIT 5
    ''')
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1][:30]:<30} | ${row[3]/1e6:.1f}M ({row[4]:.1f}%)")
    
    print("-" * 40)

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Initialize 13F Tracker database')
    parser.add_argument('--db', default='data/tracker.db', help='Database path')
    parser.add_argument('--schema', default='data/schema.sql', help='Schema file')
    parser.add_argument('--seed', default='data/seed_data.json', help='Seed data file')
    parser.add_argument('--verify', action='store_true', help='Verify after init')
    parser.add_argument('--force', action='store_true', help='Force overwrite existing database')
    
    args = parser.parse_args()
    
    print("🐋 Hedge Fund 13F Tracker - Database Initialization\n")
    
    try:
        # Initialize database
        conn = init_database(args.db, args.schema, force=args.force)
        
        # Seed data
        seed_data(conn, args.seed)
        
        # Verify if requested
        if args.verify:
            verify_database(conn)
        
        conn.close()
        print(f"\n✅ Database ready: {args.db}")
        print("\nNext steps:")
        print("  1. Run: ./scripts/hf-tracker list-funds")
        print("  2. Run: ./scripts/hf-tracker holdings --fund atreides-management")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main())
