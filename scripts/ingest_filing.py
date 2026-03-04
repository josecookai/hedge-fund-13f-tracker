#!/usr/bin/env python3
"""
13F Filing Ingestion - Import 13F data from various sources
Supports: SEC EDGAR, CSV files, JSON files
"""
import sqlite3
import json
import csv
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# Import local modules
import sys
sys.path.insert(0, str(Path(__file__).parent))

from parse_13f import parse_13f_file
from fetch_sec import SECEdgarFetcher, fetch_fund_13f


class FilingIngester:
    """Ingest 13F filings into database"""
    
    def __init__(self, db_path: str = 'data/tracker.db'):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
    
    def close(self):
        self.conn.close()
    
    def _generate_id(self, fund_id: str, quarter: str, ticker: str) -> str:
        """Generate unique ID for position"""
        return f"{fund_id}-{quarter}-{ticker.lower()}"
    
    def get_fund_cik(self, fund_id: str) -> Optional[str]:
        """Get CIK for fund from database"""
        self.cursor.execute('SELECT cik FROM funds WHERE id = ?', (fund_id,))
        result = self.cursor.fetchone()
        return result[0] if result else None
    
    def import_from_sec(self, fund_id: str, quarter: str) -> bool:
        """Import filing directly from SEC EDGAR"""
        print(f"Importing {fund_id} for {quarter} from SEC EDGAR...")
        
        # Get fund CIK
        cik = self.get_fund_cik(fund_id)
        if not cik:
            print(f"❌ No CIK found for fund: {fund_id}")
            return False
        
        # Fetch from SEC
        result = fetch_fund_13f(cik)
        if 'error' in result:
            print(f"❌ Error fetching from SEC: {result['error']}")
            return False
        
        # Parse holdings
        holdings = result['holdings']['holdings']
        if not holdings:
            print("❌ No holdings found in filing")
            return False
        
        # Calculate totals
        total_value = sum(h['value'] for h in holdings)
        
        # Insert filing record
        filing_id = f"{fund_id}-{quarter}"
        metadata = result['filing_metadata']
        
        self.cursor.execute('''
            INSERT OR REPLACE INTO filings 
            (id, fund_id, quarter, filing_date, report_date, total_value, position_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            filing_id,
            fund_id,
            quarter,
            metadata.get('filing_date', datetime.now().isoformat()),
            quarter.replace('-Q', '-'),  # Approximate report date
            total_value,
            len(holdings)
        ))
        
        # Insert positions (top 50 for now)
        sorted_holdings = sorted(holdings, key=lambda x: x['value'], reverse=True)
        
        for rank, holding in enumerate(sorted_holdings, 1):
            position_id = self._generate_id(fund_id, quarter, holding['cusip'] or 'UNKNOWN')
            portfolio_pct = (holding['value'] / total_value * 100) if total_value > 0 else 0
            
            self.cursor.execute('''
                INSERT OR REPLACE INTO positions
                (id, filing_id, ticker, cusip, company_name, shares, value, portfolio_pct, rank)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                position_id,
                filing_id,
                holding.get('ticker', self._cusip_to_ticker(holding.get('cusip', ''))),
                holding.get('cusip'),
                holding.get('company_name'),
                holding.get('shares', 0),
                holding.get('value', 0),
                portfolio_pct,
                rank
            ))
        
        self.conn.commit()
        print(f"✅ Imported {len(sorted_holdings)} positions")
        print(f"   Total value: ${total_value:,.0f}")
        return True
    
    def import_from_csv(self, filepath: str, fund_id: str, quarter: str) -> bool:
        """Import positions from CSV file"""
        print(f"Importing from CSV: {filepath}")
        
        try:
            with open(filepath, 'r') as f:
                reader = csv.DictReader(f)
                positions = list(reader)
            
            return self._import_positions(positions, fund_id, quarter)
            
        except Exception as e:
            print(f"❌ Error importing CSV: {e}")
            return False
    
    def import_from_json(self, filepath: str, fund_id: str, quarter: str) -> bool:
        """Import positions from JSON file"""
        print(f"Importing from JSON: {filepath}")
        
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            positions = data.get('positions', data.get('holdings', []))
            return self._import_positions(positions, fund_id, quarter)
            
        except Exception as e:
            print(f"❌ Error importing JSON: {e}")
            return False
    
    def _import_positions(self, positions: List[Dict], fund_id: str, quarter: str) -> bool:
        """Import list of positions to database"""
        
        if not positions:
            print("❌ No positions to import")
            return False
        
        filing_id = f"{fund_id}-{quarter}"
        
        # Calculate totals
        total_value = sum(
            int(p.get('value', 0)) if isinstance(p.get('value'), (int, float, str)) else 0 
            for p in positions
        )
        
        # Insert filing record
        self.cursor.execute('''
            INSERT OR REPLACE INTO filings 
            (id, fund_id, quarter, total_value, position_count)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            filing_id,
            fund_id,
            quarter,
            total_value,
            len(positions)
        ))
        
        # Insert positions
        for rank, pos in enumerate(positions, 1):
            ticker = pos.get('ticker', pos.get('symbol', ''))
            cusip = pos.get('cusip', '')
            position_id = self._generate_id(fund_id, quarter, ticker or cusip or f"pos{rank}")
            
            value = pos.get('value', 0)
            if isinstance(value, str):
                value = int(value.replace(',', ''))
            
            shares = pos.get('shares', 0)
            if isinstance(shares, str):
                shares = int(shares.replace(',', ''))
            
            portfolio_pct = (value / total_value * 100) if total_value > 0 else 0
            
            self.cursor.execute('''
                INSERT OR REPLACE INTO positions
                (id, filing_id, ticker, cusip, company_name, shares, value, portfolio_pct, rank)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                position_id,
                filing_id,
                ticker,
                cusip,
                pos.get('company_name', pos.get('name', '')),
                shares,
                value,
                portfolio_pct,
                pos.get('rank', rank)
            ))
        
        self.conn.commit()
        print(f"✅ Imported {len(positions)} positions")
        return True
    
    def _cusip_to_ticker(self, cusip: str) -> str:
        """Convert CUSIP to ticker (placeholder - would need mapping file)"""
        # This is a simplified mapping - in production use a proper CUSIP->ticker database
        mapping = {
            '67066G104': 'NVDA',
            '30303M102': 'META',
            '023135106': 'AMZN',
            '594918104': 'MSFT',
            '11135F101': 'AVGO',
            '87989T104': 'TEM',
            '92840M102': 'VST',
            '03852U106': 'APP',
            '19260Q107': 'COIN',
            '125269100': 'CF',
        }
        return mapping.get(cusip, cusip)


def main():
    parser = argparse.ArgumentParser(description='Ingest 13F filings')
    parser.add_argument('--fund', required=True, help='Fund ID (e.g., atreides-management)')
    parser.add_argument('--quarter', required=True, help='Quarter (e.g., 2024-Q4)')
    parser.add_argument('--source', choices=['sec', 'csv', 'json', 'auto'], 
                       default='auto', help='Data source')
    parser.add_argument('--file', help='Path to CSV/JSON file (if not using SEC)')
    parser.add_argument('--db', default='data/tracker.db', help='Database path')
    
    args = parser.parse_args()
    
    print(f"🐋 13F Filing Ingestion")
    print(f"Fund: {args.fund}")
    print(f"Quarter: {args.quarter}")
    print(f"Source: {args.source}\n")
    
    ingester = FilingIngester(args.db)
    
    success = False
    
    if args.source == 'sec' or (args.source == 'auto' and not args.file):
        success = ingester.import_from_sec(args.fund, args.quarter)
    
    elif args.source == 'csv' or (args.file and args.file.endswith('.csv')):
        if not args.file:
            print("❌ --file required for CSV import")
            return 1
        success = ingester.import_from_csv(args.file, args.fund, args.quarter)
    
    elif args.source == 'json' or (args.file and args.file.endswith('.json')):
        if not args.file:
            print("❌ --file required for JSON import")
            return 1
        success = ingester.import_from_json(args.file, args.fund, args.quarter)
    
    ingester.close()
    
    if success:
        print(f"\n✅ Successfully ingested {args.fund} {args.quarter}")
        return 0
    else:
        print(f"\n❌ Failed to ingest")
        return 1


if __name__ == '__main__':
    exit(main())
