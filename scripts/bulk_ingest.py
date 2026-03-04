#!/usr/bin/env python3
"""
SEC 13F Bulk Data Downloader
Simple quarterly job - run 4 times per year
"""
import os
import sys
import gzip
import shutil
import sqlite3
import requests
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional

# Config
SEC_FEED_URL = "https://www.sec.gov/Archives/edgar/Feed/13F/"
QUARTER_MAP = {'Q1': '0331', 'Q2': '0630', 'Q3': '0930', 'Q4': '1231'}

def get_quarter_from_date(date: datetime) -> str:
    """Get quarter string from date"""
    year = date.year
    month = date.month
    if month <= 3:
        return f"{year}-Q1"
    elif month <= 6:
        return f"{year}-Q2"
    elif month <= 9:
        return f"{year}-Q3"
    else:
        return f"{year}-Q4"

def download_bulk_file(quarter: str, output_dir: str = "data/sec_bulk") -> Optional[str]:
    """
    Download SEC 13F bulk file for quarter
    
    Files are named: 13f-hr-{year}-{quarter}.txt.gz
    Example: 13f-hr-2024-q4.txt.gz
    """
    year, q = quarter.split('-')
    
    # Try different filename formats
    filenames = [
        f"13f-hr-{year}-{q.lower()}.txt.gz",
        f"13f-hr-{year}{QUARTER_MAP[q.upper()]}.txt.gz",
    ]
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    headers = {
        'User-Agent': 'HedgeFundTracker contact@example.com',
        'Accept-Encoding': 'gzip, deflate'
    }
    
    for filename in filenames:
        url = f"{SEC_FEED_URL}{filename}"
        local_path = output_path / filename
        
        if local_path.exists():
            print(f"✅ File already exists: {local_path}")
            return str(local_path)
        
        print(f"📥 Downloading: {url}")
        try:
            response = requests.get(url, headers=headers, timeout=300, stream=True)
            if response.status_code == 200:
                with open(local_path, 'wb') as f:
                    shutil.copyfileobj(response.raw, f)
                print(f"✅ Downloaded: {local_path} ({local_path.stat().st_size / 1024 / 1024:.1f} MB)")
                return str(local_path)
            else:
                print(f"⚠️  Failed: {response.status_code}")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    return None

def parse_bulk_file(filepath: str) -> List[Dict]:
    """
    Parse SEC 13F bulk file
    Returns list of holdings with: cik, fund_name, ticker, shares, value, etc.
    """
    print(f"📖 Parsing: {filepath}")
    
    holdings = []
    
    # Open gzip or plain text
    if filepath.endswith('.gz'):
        import gzip
        opener = lambda: gzip.open(filepath, 'rt', encoding='latin-1')
    else:
        opener = lambda: open(filepath, 'r', encoding='latin-1')
    
    with opener() as f:
        current_fund = None
        
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            # SEC 13F format has fixed-width fields
            # This is a simplified parser
            if len(line) >= 200:  # Likely a holding record
                try:
                    # Parse fields (adjust indices based on actual format)
                    cik = line[0:10].strip()
                    fund_name = line[10:80].strip()
                    cusip = line[80:89].strip()
                    name = line[89:130].strip()
                    title = line[130:160].strip()
                    shares = line[160:175].strip()
                    value = line[175:190].strip()
                    
                    if cik and cusip:
                        holdings.append({
                            'cik': cik,
                            'fund_name': fund_name,
                            'cusip': cusip,
                            'company_name': name,
                            'title': title,
                            'shares': int(shares) if shares.isdigit() else 0,
                            'value': int(value) * 1000 if value.isdigit() else 0,  # Value is in thousands
                        })
                except Exception as e:
                    continue
    
    print(f"✅ Parsed {len(holdings):,} holdings")
    return holdings

def update_database(holdings: List[Dict], quarter: str, db_path: str = "data/tracker.db"):
    """Update database with bulk holdings"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get CIK to fund_id mapping
    cursor.execute('SELECT cik, id FROM funds WHERE cik IS NOT NULL')
    cik_map = {row[0].lstrip('0'): row[1] for row in cursor.fetchall()}
    
    updated = 0
    skipped = 0
    
    # Group by fund
    from collections import defaultdict
    fund_holdings = defaultdict(list)
    
    for h in holdings:
        cik = h['cik'].lstrip('0')
        if cik in cik_map:
            fund_id = cik_map[cik]
            fund_holdings[fund_id].append(h)
    
    print(f"\n📊 Updating {len(fund_holdings)} funds...")
    
    for fund_id, positions in fund_holdings.items():
        filing_id = f"{fund_id}-{quarter}"
        total_value = sum(p['value'] for p in positions)
        
        # Insert filing
        cursor.execute('''
            INSERT OR REPLACE INTO filings 
            (id, fund_id, quarter, filing_date, report_date, total_value, position_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            filing_id,
            fund_id,
            quarter,
            datetime.now().strftime('%Y-%m-%d'),
            quarter.replace('-Q', '-') + '-30',  # Approximate
            total_value,
            len(positions)
        ))
        
        # Clear old positions for this filing
        cursor.execute('DELETE FROM positions WHERE filing_id = ?', (filing_id,))
        
        # Insert new positions
        for rank, p in enumerate(sorted(positions, key=lambda x: x['value'], reverse=True), 1):
            position_id = f"{filing_id}-{p['cusip']}"
            cursor.execute('''
                INSERT INTO positions (id, filing_id, ticker, cusip, company_name, 
                                     shares, value, portfolio_pct, rank)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                position_id,
                filing_id,
                p['cusip'],  # Using CUSIP as ticker (need mapping)
                p['cusip'],
                p['company_name'][:50],
                p['shares'],
                p['value'],
                (p['value'] / total_value * 100) if total_value > 0 else 0,
                rank
            ))
        
        updated += 1
        print(f"  ✅ {fund_id}: {len(positions)} positions, ${total_value/1e9:.2f}B")
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ Updated {updated} funds, skipped {skipped} CIKs")

def main():
    parser = argparse.ArgumentParser(description='SEC 13F Bulk Data Downloader')
    parser.add_argument('--quarter', help='Quarter (e.g., 2024-Q4), default: latest')
    parser.add_argument('--download-only', action='store_true', help='Only download, don\'t parse')
    parser.add_argument('--parse-only', help='Parse existing file')
    parser.add_argument('--db', default='data/tracker.db', help='Database path')
    
    args = parser.parse_args()
    
    if args.parse_only:
        # Parse existing file
        holdings = parse_bulk_file(args.parse_only)
        quarter = input("Enter quarter (e.g., 2024-Q4): ")
        update_database(holdings, quarter, args.db)
        return
    
    # Determine quarter
    if args.quarter:
        quarter = args.quarter
    else:
        # Default to previous quarter
        today = datetime.now()
        quarter = get_quarter_from_date(today - timedelta(days=45))
    
    print(f"🐋 SEC 13F Bulk Downloader - {quarter}\n")
    
    # Download
    filepath = download_bulk_file(quarter)
    if not filepath:
        print("❌ Failed to download")
        sys.exit(1)
    
    if args.download_only:
        print(f"✅ Downloaded to: {filepath}")
        return
    
    # Parse and update
    holdings = parse_bulk_file(filepath)
    if holdings:
        update_database(holdings, quarter, args.db)
        print(f"\n✅ Bulk import complete for {quarter}")
    else:
        print("❌ No holdings parsed")

if __name__ == '__main__':
    main()
