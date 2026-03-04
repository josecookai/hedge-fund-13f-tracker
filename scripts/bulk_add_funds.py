#!/usr/bin/env python3
"""
Bulk add recommended hedge funds to database
"""
import sqlite3
import json
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / 'data' / 'tracker.db'

def bulk_add_funds():
    """Add all recommended funds to database"""
    
    # Load fund registry
    registry_path = Path(__file__).parent.parent / 'config' / 'fund_registry.json'
    with open(registry_path, 'r') as f:
        data = json.load(f)
    
    # Connect to database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get already existing funds
    cursor.execute('SELECT id FROM funds')
    existing = {row[0] for row in cursor.fetchall()}
    
    added = []
    skipped = []
    
    print("🐋 Bulk Adding Hedge Funds to 13F Tracker\n")
    
    # Add verified funds first
    print("=== Adding Verified Funds ===")
    for fund in data['verified_funds']:
        if fund['id'] in existing:
            skipped.append(fund['id'])
            continue
        
        cursor.execute('''
            INSERT INTO funds (id, name, manager, strategy, aum, cik)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            fund['id'],
            fund['name'],
            fund.get('manager'),
            fund.get('strategy'),
            fund.get('aum_usd'),
            fund.get('cik')
        ))
        added.append(fund['id'])
        aum = fund.get('aum_usd', 0)
        aum_str = f"${aum/1e9:.1f}B" if aum >= 1e9 else f"${aum/1e6:.0f}M"
        print(f"  ✅ {fund['name']} ({aum_str})")
    
    # Add recommended funds
    print("\n=== Adding Recommended Funds ===")
    for fund in data['additional_recommended_funds']:
        if fund['id'] in existing:
            skipped.append(fund['id'])
            continue
        
        cursor.execute('''
            INSERT INTO funds (id, name, manager, strategy, aum, cik)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            fund['id'],
            fund['name'],
            fund.get('manager'),
            fund.get('strategy'),
            fund.get('aum_usd'),
            fund.get('cik')
        ))
        added.append(fund['id'])
        aum = fund.get('aum_usd', 0)
        aum_str = f"${aum/1e9:.1f}B" if aum >= 1e9 else f"${aum/1e6:.0f}M"
        print(f"  ✅ {fund['name']} ({aum_str})")
    
    conn.commit()
    
    # Show summary
    print(f"\n=== Summary ===")
    print(f"Added: {len(added)} funds")
    if skipped:
        print(f"Skipped (already exists): {len(skipped)} funds")
    
    # Show current fund list
    print(f"\n=== Current Fund List ({len(existing) + len(added)} total) ===")
    cursor.execute('SELECT id, name, manager, aum FROM funds ORDER BY aum DESC')
    for row in cursor.fetchall():
        aum = row[3] or 0
        aum_str = f"${aum/1e9:.1f}B" if aum >= 1e9 else f"${aum/1e6:.0f}M"
        print(f"  • {row[0]:30} {row[1][:35]:35} {aum_str:>10}")
    
    conn.close()
    print(f"\n✅ Bulk add complete!")
    print(f"\nNext steps:")
    print(f"  1. Import holdings: python scripts/ingest_filing.py --fund <fund-id> --quarter 2024-Q4 --source sec")
    print(f"  2. View all funds: ./scripts/hf-tracker list-funds")

if __name__ == '__main__':
    bulk_add_funds()
