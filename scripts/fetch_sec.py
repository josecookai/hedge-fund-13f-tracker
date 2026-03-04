#!/usr/bin/env python3
"""
SEC EDGAR Fetcher - Retrieve 13F filings from SEC
Uses SEC EDGAR API and web scraping as fallback
"""
import requests
import time
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pathlib import Path

class SECEdgarFetcher:
    """Fetch 13F filings from SEC EDGAR"""
    
    BASE_URL = "https://www.sec.gov/cgi-bin/browse-edgar"
    ARCHIVES_URL = "https://www.sec.gov/Archives/edgar/data"
    
    def __init__(self, user_agent: str = "HedgeFundTracker contact@example.com"):
        self.user_agent = user_agent
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': user_agent
        })
        # SEC rate limit: 10 requests per second
        self.last_request_time = 0
        self.min_delay = 0.1  # 100ms between requests
    
    def _rate_limit(self):
        """Enforce SEC rate limiting"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_delay:
            time.sleep(self.min_delay - elapsed)
        self.last_request_time = time.time()
    
    def search_filings(self, cik: str, filing_type: str = "13F-HR", 
                       count: int = 10) -> List[Dict]:
        """
        Search for 13F filings by CIK
        Returns list of filing metadata
        """
        self._rate_limit()
        
        params = {
            'action': 'getcompany',
            'CIK': cik,
            'type': filing_type,
            'dateb': '',
            'owner': 'include',
            'count': count,
            'output': 'atom'
        }
        
        try:
            response = self.session.get(self.BASE_URL, params=params)
            response.raise_for_status()
            
            # Parse XML response
            import xml.etree.ElementTree as ET
            root = ET.fromstring(response.content)
            
            # Atom namespace
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            
            filings = []
            for entry in root.findall('atom:entry', ns):
                title = entry.find('atom:title', ns)
                link = entry.find('atom:link', ns)
                updated = entry.find('atom:updated', ns)
                
                if title is not None and link is not None:
                    # Extract accession number from link
                    href = link.get('href', '')
                    accession_match = re.search(r'/(\d+)-(\d+)-(\d+)', href)
                    accession = None
                    if accession_match:
                        accession = f"{accession_match.group(1)}{accession_match.group(2)}{accession_match.group(3)}"
                    
                    filings.append({
                        'title': title.text,
                        'filing_url': href,
                        'filing_date': updated.text if updated is not None else None,
                        'accession_number': accession,
                        'cik': cik
                    })
            
            return filings
            
        except Exception as e:
            print(f"Error searching filings: {e}")
            return []
    
    def get_filing_document(self, cik: str, accession: str, 
                           doc_type: str = 'form13fInfoTable.xml') -> Optional[str]:
        """
        Fetch specific document from a filing
        Returns raw content or None if not found
        """
        self._rate_limit()
        
        # Format CIK (pad to 10 digits)
        cik_padded = cik.zfill(10)
        
        # Format accession (remove dashes)
        accession_clean = accession.replace('-', '')
        
        url = f"{self.ARCHIVES_URL}/{cik_padded}/{accession_clean}/{doc_type}"
        
        try:
            response = self.session.get(url)
            if response.status_code == 200:
                return response.text
            
            # Try alternative filenames
            alternatives = [
                'infotable.xml',
                'InfoTable.xml',
                f"{doc_type}.xml",
                'form13fInfoTable.htm'
            ]
            
            for alt in alternatives:
                self._rate_limit()
                alt_url = f"{self.ARCHIVES_URL}/{cik_padded}/{accession_clean}/{alt}"
                response = self.session.get(alt_url)
                if response.status_code == 200:
                    return response.text
            
            return None
            
        except Exception as e:
            print(f"Error fetching document: {e}")
            return None
    
    def download_filing(self, cik: str, accession: str, 
                       output_dir: str = 'data/sec_filings') -> Optional[str]:
        """
        Download and save 13F filing to local file
        Returns path to saved file or None
        """
        content = self.get_filing_document(cik, accession)
        if content is None:
            return None
        
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Save file
        filename = f"{cik}_{accession}_13f.xml"
        filepath = output_path / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return str(filepath)
    
    def get_latest_filing(self, cik: str) -> Optional[Dict]:
        """Get most recent 13F filing for a fund"""
        filings = self.search_filings(cik, count=1)
        return filings[0] if filings else None


def fetch_fund_13f(cik: str, quarter: Optional[str] = None) -> Dict:
    """
    High-level function to fetch 13F for a fund
    
    Args:
        cik: Fund CIK number
        quarter: Optional specific quarter (e.g., "2024-Q4")
    
    Returns:
        Dict with filing metadata and holdings
    """
    fetcher = SECEdgarFetcher()
    
    # Get latest filing
    latest = fetcher.get_latest_filing(cik)
    if not latest:
        return {'error': 'No filings found'}
    
    # Download document
    filepath = fetcher.download_filing(
        latest['cik'], 
        latest['accession_number']
    )
    
    if not filepath:
        return {'error': 'Could not download filing'}
    
    # Parse the filing
    from parse_13f import parse_13f_file
    holdings = parse_13f_file(filepath)
    
    return {
        'fund_cik': cik,
        'filing_metadata': latest,
        'local_path': filepath,
        'holdings': holdings
    }


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python fetch_sec.py <CIK>")
        print("Example: python fetch_sec.py 0001761945")
        sys.exit(1)
    
    cik = sys.argv[1]
    
    print(f"Fetching 13F filings for CIK: {cik}")
    
    fetcher = SECEdgarFetcher()
    
    # Search for filings
    filings = fetcher.search_filings(cik)
    print(f"\nFound {len(filings)} filings:")
    
    for i, filing in enumerate(filings[:3], 1):
        print(f"\n{i}. {filing['title']}")
        print(f"   Date: {filing['filing_date']}")
        print(f"   Accession: {filing['accession_number']}")
        print(f"   URL: {filing['filing_url']}")
    
    # Download latest
    if filings:
        print(f"\nDownloading latest filing...")
        filepath = fetcher.download_filing(cik, filings[0]['accession_number'])
        if filepath:
            print(f"Saved to: {filepath}")
            
            # Parse and show summary
            from parse_13f import parse_13f_file
            result = parse_13f_file(filepath)
            print(f"\nParsed {result['total_positions']} positions")
        else:
            print("Failed to download")
