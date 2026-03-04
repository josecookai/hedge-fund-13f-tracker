#!/usr/bin/env python3
"""
13F XML Parser - Parse SEC EDGAR 13F filings
Supports both XML and TXT formats from SEC
"""
import xml.etree.ElementTree as ET
import re
from datetime import datetime
from typing import Dict, List, Optional

class F13Parser:
    """Parse 13F filings from SEC EDGAR"""
    
    def __init__(self):
        self.ns = {
            'ns': 'http://www.sec.gov/edgar/document/thirteenf/informationtable'
        }
    
    def parse_xml(self, xml_content: str) -> Dict:
        """
        Parse 13F XML information table
        Returns structured dict with holdings data
        """
        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError as e:
            # Try parsing as HTML table (some filings use different format)
            return self._parse_html_table(xml_content)
        
        holdings = []
        
        # Find all infoTable entries
        info_tables = root.findall('.//ns:infoTable', self.ns)
        if not info_tables:
            # Try without namespace
            info_tables = root.findall('.//infoTable')
        
        for table in info_tables:
            holding = self._parse_info_table(table)
            if holding:
                holdings.append(holding)
        
        return {
            'holdings': holdings,
            'total_positions': len(holdings),
            'parsed_at': datetime.now().isoformat()
        }
    
    def _parse_info_table(self, table) -> Optional[Dict]:
        """Parse individual infoTable entry"""
        try:
            # Helper to get text from element
            def get_text(tag_name, ns=None):
                if ns:
                    elem = table.find(f'ns:{tag_name}', {'ns': ns})
                else:
                    elem = table.find(tag_name)
                    if elem is None:
                        elem = table.find(f'.//{tag_name}')
                return elem.text.strip() if elem is not None and elem.text else None
            
            # Get namespace from table
            ns = 'http://www.sec.gov/edgar/document/thirteenf/informationtable'
            
            name_of_issuer = get_text('nameOfIssuer', ns)
            cusip = get_text('cusip', ns)
            
            # Shares
            ssh_prnamt = get_text('sshPrnamt', ns)
            shares = int(ssh_prnamt) if ssh_prnamt else 0
            
            # Value (in thousands)
            value_elem = get_text('value', ns)
            value = int(value_elem) * 1000 if value_elem else 0
            
            # Investment discretion
            investment_discretion = get_text('investmentDiscretion', ns)
            
            # Voting authority
            sole_voting = get_text('Sole', ns) or '0'
            shared_voting = get_text('Shared', ns) or '0'
            none_voting = get_text('None', ns) or '0'
            
            # Security type
            title_class = get_text('titleOfClass', ns)
            
            return {
                'company_name': name_of_issuer,
                'cusip': cusip,
                'shares': shares,
                'value': value,
                'title_class': title_class or 'COM',
                'investment_discretion': investment_discretion or 'SOLE',
                'voting_authority': {
                    'sole': int(sole_voting),
                    'shared': int(shared_voting),
                    'none': int(none_voting)
                }
            }
        except Exception as e:
            print(f"Error parsing infoTable: {e}")
            return None
    
    def _parse_html_table(self, content: str) -> Dict:
        """Fallback parser for HTML table format"""
        holdings = []
        # This is a simplified parser - full implementation would use BeautifulSoup
        return {
            'holdings': holdings,
            'total_positions': len(holdings),
            'parsed_at': datetime.now().isoformat(),
            'note': 'HTML parsing not fully implemented'
        }
    
    def parse_txt_format(self, txt_content: str) -> Dict:
        """
        Parse older 13F TXT format (pre-2013)
        Uses regex pattern matching
        """
        holdings = []
        lines = txt_content.split('\n')
        
        # Look for table entries (typically start after header)
        in_table = False
        for line in lines:
            line = line.strip()
            
            # Check for table start/end markers
            if 'NAME OF ISSUER' in line and 'CUSIP' in line:
                in_table = True
                continue
            
            if in_table and line and not line.startswith('<'):
                # Try to parse table row
                parts = line.split()
                if len(parts) >= 4:
                    try:
                        # Last numeric fields are usually shares and value
                        shares = int(parts[-2].replace(',', ''))
                        value = int(parts[-1].replace(',', '')) * 1000
                        cusip = parts[-3]
                        name = ' '.join(parts[:-3])
                        
                        holdings.append({
                            'company_name': name,
                            'cusip': cusip,
                            'shares': shares,
                            'value': value,
                            'title_class': 'COM',
                            'investment_discretion': 'SOLE',
                            'voting_authority': {'sole': 0, 'shared': 0, 'none': 0}
                        })
                    except ValueError:
                        continue
        
        return {
            'holdings': holdings,
            'total_positions': len(holdings),
            'parsed_at': datetime.now().isoformat()
        }


def parse_13f_file(filepath: str) -> Dict:
    """
    Parse a 13F filing from file
    Auto-detects format (XML or TXT)
    """
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    parser = F13Parser()
    
    # Detect format
    if '<informationTable' in content or '<?xml' in content:
        return parser.parse_xml(content)
    else:
        return parser.parse_txt_format(content)


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python parse_13f.py <13f_file.xml>")
        sys.exit(1)
    
    filepath = sys.argv[1]
    result = parse_13f_file(filepath)
    
    print(f"Parsed {result['total_positions']} positions")
    print(f"\nTop 5 holdings:")
    for i, holding in enumerate(result['holdings'][:5], 1):
        print(f"{i}. {holding['company_name']} ({holding['cusip']})")
        print(f"   Shares: {holding['shares']:,} | Value: ${holding['value']:,.0f}")
