#!/usr/bin/env python3
"""
WhaleWisdom Integration - Fetch 13F data from WhaleWisdom
Falls back to scraping if no API available
"""
import requests
import time
import re
import json
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from dataclasses import dataclass


@dataclass
class WhaleWisdomHolding:
    """Represents a holding from WhaleWisdom"""
    ticker: str
    company_name: str
    shares: int
    value: int
    portfolio_pct: float
    quarter: str
    
    def to_dict(self) -> Dict:
        return {
            'ticker': self.ticker,
            'company_name': self.company_name,
            'shares': self.shares,
            'value': self.value,
            'portfolio_pct': self.portfolio_pct,
            'quarter': self.quarter
        }


class WhaleWisdomSource:
    """Fetch 13F data from WhaleWisdom"""
    
    BASE_URL = "https://whalewisdom.com"
    
    def __init__(self, user_agent: str = "HedgeFundTracker/1.0"):
        self.user_agent = user_agent
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        })
        self.last_request_time = 0
        self.min_delay = 2.0  # 2 seconds between requests (be nice to WhaleWisdom)
    
    def _rate_limit(self):
        """Enforce rate limiting"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_delay:
            time.sleep(self.min_delay - elapsed)
        self.last_request_time = time.time()
    
    def get_fund_url(self, fund_name: str) -> Optional[str]:
        """
        Get WhaleWisdom URL for a fund
        
        Converts fund name to URL slug
        """
        # Common fund slug mappings
        slug_mappings = {
            'atreides-management': 'atreides-management-lp',
            'monolith-management': 'monolith-management-ltd',
            'wt-asset-management': 'wt-asset-management-ltd',
            'situational-awareness': 'situational-awareness-lp',
            'tiger-global': 'tiger-global-management-llc',
            'coatue-management': 'coatue-management-llc',
            'tci-fund': 'childrens-investment-fund-management-uk-llp',
            'viking-global': 'viking-global-investors-lp',
            'greenlight-capital': 'greenlight-capital-inc',
            'baupost-group': 'baupost-group-llc',
            'lone-pine-capital': 'lone-pine-capital-llc',
            'd1-capital': 'd1-capital-partners-lp',
        }
        
        if fund_name in slug_mappings:
            return f"{self.BASE_URL}/filer/{slug_mappings[fund_name]}"
        
        # Try to construct URL from name
        slug = fund_name.lower().replace(' ', '-').replace(',', '').replace('.', '')
        return f"{self.BASE_URL}/filer/{slug}"
    
    def fetch_holdings_html(self, fund_url: str) -> Optional[str]:
        """Fetch raw HTML from WhaleWisdom"""
        self._rate_limit()
        
        try:
            response = self.session.get(fund_url, timeout=30)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"Error fetching from WhaleWisdom: {e}")
            return None
    
    def parse_holdings_from_html(self, html: str, quarter: str) -> List[WhaleWisdomHolding]:
        """
        Parse holdings from WhaleWisdom HTML
        
        Note: This is a best-effort parser. WhaleWisdom may change their HTML structure.
        """
        holdings = []
        
        try:
            # Try to extract JSON data embedded in page
            # WhaleWisdom sometimes embeds data in script tags
            json_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.+?});', html)
            if json_match:
                data = json.loads(json_match.group(1))
                # Extract holdings from JSON structure
                # This would need to be adapted to actual WhaleWisdom structure
                return self._parse_json_holdings(data, quarter)
            
            # Fallback: Parse HTML tables
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'lxml')
            
            # Look for holdings table
            tables = soup.find_all('table')
            for table in tables:
                # Check if this is a holdings table
                headers = [th.get_text(strip=True).lower() for th in table.find_all('th')]
                if 'stock' in headers or 'ticker' in headers or 'company' in headers:
                    rows = table.find_all('tr')[1:]  # Skip header
                    
                    for row in rows:
                        cells = row.find_all('td')
                        if len(cells) >= 4:
                            try:
                                # Extract data
                                ticker = cells[0].get_text(strip=True)
                                company = cells[1].get_text(strip=True) if len(cells) > 1 else ticker
                                
                                # Shares
                                shares_text = cells[2].get_text(strip=True).replace(',', '').replace('(', '').replace(')', '')
                                shares = int(shares_text) if shares_text.isdigit() else 0
                                
                                # Value (in thousands usually)
                                value_text = cells[3].get_text(strip=True).replace(',', '').replace('$', '')
                                value = int(float(value_text) * 1000) if value_text.replace('.', '').isdigit() else 0
                                
                                # Portfolio percentage
                                pct_text = cells[4].get_text(strip=True).replace('%', '') if len(cells) > 4 else '0'
                                pct = float(pct_text) if pct_text.replace('.', '').isdigit() else 0
                                
                                holdings.append(WhaleWisdomHolding(
                                    ticker=ticker,
                                    company_name=company,
                                    shares=shares,
                                    value=value,
                                    portfolio_pct=pct,
                                    quarter=quarter
                                ))
                            except (ValueError, IndexError):
                                continue
        except Exception as e:
            print(f"Error parsing HTML: {e}")
        
        return holdings
    
    def _parse_json_holdings(self, data: Dict, quarter: str) -> List[WhaleWisdomHolding]:
        """Parse holdings from JSON data"""
        holdings = []
        # This would be customized based on actual WhaleWisdom JSON structure
        return holdings
    
    def fetch_holdings(self, fund_id: str, quarter: str) -> List[WhaleWisdomHolding]:
        """
        Main method to fetch holdings from WhaleWisdom
        
        Args:
            fund_id: Fund identifier (e.g., 'atreides-management')
            quarter: Quarter string (e.g., '2024-Q4')
        
        Returns:
            List of WhaleWisdomHolding objects
        """
        url = self.get_fund_url(fund_id)
        if not url:
            print(f"Could not determine URL for fund: {fund_id}")
            return []
        
        print(f"Fetching from WhaleWisdom: {url}")
        
        html = self.fetch_holdings_html(url)
        if not html:
            return []
        
        holdings = self.parse_holdings_from_html(html, quarter)
        print(f"Parsed {len(holdings)} holdings from WhaleWisdom")
        
        return holdings
    
    def validate_against_sec(self, ww_holdings: List[WhaleWisdomHolding], 
                            sec_holdings: List[Dict]) -> Dict:
        """
        Cross-validate WhaleWisdom data against SEC source
        
        Returns validation report
        """
        ww_by_ticker = {h.ticker: h for h in ww_holdings}
        sec_by_ticker = {h.get('ticker', ''): h for h in sec_holdings}
        
        matched = 0
        mismatched = 0
        missing_in_ww = []
        missing_in_sec = []
        
        for ticker, ww in ww_by_ticker.items():
            if ticker in sec_by_ticker:
                sec = sec_by_ticker[ticker]
                # Check if shares match (within 1% tolerance)
                if abs(ww.shares - sec.get('shares', 0)) / max(ww.shares, 1) < 0.01:
                    matched += 1
                else:
                    mismatched += 1
            else:
                missing_in_sec.append(ticker)
        
        for ticker in sec_by_ticker:
            if ticker not in ww_by_ticker:
                missing_in_ww.append(ticker)
        
        return {
            'whalewisdom_count': len(ww_holdings),
            'sec_count': len(sec_holdings),
            'matched': matched,
            'mismatched': mismatched,
            'missing_in_whalewisdom': missing_in_ww,
            'missing_in_sec': missing_in_sec,
            'accuracy': matched / len(ww_holdings) * 100 if ww_holdings else 0
        }
    
    def export_holdings_csv(self, holdings: List[WhaleWisdomHolding], filepath: str):
        """Export holdings to CSV"""
        import csv
        
        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['ticker', 'company_name', 'shares', 'value', 'portfolio_pct', 'quarter'])
            
            for h in holdings:
                writer.writerow([h.ticker, h.company_name, h.shares, h.value, h.portfolio_pct, h.quarter])
        
        return filepath


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='WhaleWisdom Data Fetcher')
    parser.add_argument('--fund', '-f', required=True, help='Fund ID (e.g., atreides-management)')
    parser.add_argument('--quarter', '-q', default='2024-Q4', help='Quarter (e.g., 2024-Q4)')
    parser.add_argument('--export', '-e', help='Export to CSV file')
    parser.add_argument('--validate', help='Validate against SEC JSON file')
    
    args = parser.parse_args()
    
    source = WhaleWisdomSource()
    
    print(f"🐋 Fetching {args.fund} for {args.quarter} from WhaleWisdom\n")
    
    holdings = source.fetch_holdings(args.fund, args.quarter)
    
    if not holdings:
        print("❌ No holdings fetched")
        return
    
    print(f"\n✅ Fetched {len(holdings)} holdings\n")
    
    # Display top 10
    print("Top 10 Holdings:")
    print("-" * 80)
    for i, h in enumerate(holdings[:10], 1):
        value_str = f"${h.value/1e6:.1f}M" if h.value >= 1e6 else f"${h.value/1e3:.0f}K"
        print(f"{i}. {h.ticker:<6} {h.company_name[:30]:<32} {value_str:>12} ({h.portfolio_pct:.1f}%)")
    
    if args.export:
        source.export_holdings_csv(holdings, args.export)
        print(f"\n📁 Exported to {args.export}")
    
    if args.validate:
        with open(args.validate, 'r') as f:
            sec_holdings = json.load(f)
        
        report = source.validate_against_sec(holdings, sec_holdings)
        print(f"\n📊 Validation Report:")
        print(f"  WhaleWisdom: {report['whalewisdom_count']} positions")
        print(f"  SEC: {report['sec_count']} positions")
        print(f"  Matched: {report['matched']}")
        print(f"  Mismatched: {report['mismatched']}")
        print(f"  Accuracy: {report['accuracy']:.1f}%")


if __name__ == '__main__':
    main()
