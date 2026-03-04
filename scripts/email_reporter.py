#!/usr/bin/env python3
"""
Email Reports for 13F Tracker
Send daily/weekly summary reports via Resend
"""
import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

import requests

DB_PATH = Path(__file__).parent.parent / 'data' / 'tracker.db'

# Resend API configuration
RESEND_API_KEY = "re_7f2YwXF7_EA9ggrxrssr9VMMHgB4VsCeL"  # From TOOLS.md
RESEND_API_URL = "https://api.resend.com/emails"
FROM_EMAIL = "13f-tracker@smrti.io"


@dataclass
class ReportConfig:
    """Email report configuration"""
    recipient: str
    report_type: str  # daily, weekly, monthly
    funds: List[str]  # Fund IDs to include
    tickers: List[str]  # Tickers to watch
    include_changes: bool
    include_consensus: bool


class EmailReporter:
    """Generate and send email reports"""
    
    def __init__(self, api_key: str = RESEND_API_KEY, db_path: Path = DB_PATH):
        self.api_key = api_key
        self.db_path = db_path
        self.from_email = FROM_EMAIL
    
    def get_db(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def generate_daily_report(self) -> Dict:
        """Generate daily summary report"""
        conn = self.get_db()
        cursor = conn.cursor()
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Get latest filings
        cursor.execute('''
            SELECT f.name, fil.quarter, fil.filing_date, fil.total_value, fil.position_count
            FROM filings fil
            JOIN funds f ON fil.fund_id = f.id
            ORDER BY fil.filing_date DESC
            LIMIT 10
        ''')
        recent_filings = [dict(row) for row in cursor.fetchall()]
        
        # Get top consensus holdings
        cursor.execute('''
            SELECT p.ticker, COUNT(DISTINCT fil.fund_id) as fund_count,
                   SUM(p.value) as total_value,
                   AVG(p.portfolio_pct) as avg_weight
            FROM positions p
            JOIN filings fil ON p.filing_id = fil.id
            GROUP BY p.ticker
            HAVING fund_count >= 2
            ORDER BY fund_count DESC, total_value DESC
            LIMIT 10
        ''')
        consensus = [dict(row) for row in cursor.fetchall()]
        
        # Get largest positions
        cursor.execute('''
            SELECT f.name as fund_name, p.ticker, p.value, p.portfolio_pct, fil.quarter
            FROM positions p
            JOIN filings fil ON p.filing_id = fil.id
            JOIN funds f ON fil.fund_id = f.id
            ORDER BY p.value DESC
            LIMIT 10
        ''')
        top_positions = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return {
            'date': today,
            'title': f'13F Tracker Daily Report - {today}',
            'recent_filings': recent_filings,
            'consensus': consensus,
            'top_positions': top_positions
        }
    
    def generate_fund_report(self, fund_id: str, quarter: Optional[str] = None) -> Dict:
        """Generate detailed report for a specific fund"""
        conn = self.get_db()
        cursor = conn.cursor()
        
        # Get fund info
        cursor.execute('SELECT * FROM funds WHERE id = ?', (fund_id,))
        fund = cursor.fetchone()
        
        if not fund:
            conn.close()
            return None
        
        # Determine quarter
        if not quarter:
            cursor.execute('''
                SELECT quarter FROM filings 
                WHERE fund_id = ? 
                ORDER BY quarter DESC LIMIT 1
            ''', (fund_id,))
            result = cursor.fetchone()
            quarter = result['quarter'] if result else None
        
        if not quarter:
            conn.close()
            return None
        
        # Get holdings
        cursor.execute('''
            SELECT p.*
            FROM positions p
            JOIN filings f ON p.filing_id = f.id
            WHERE f.fund_id = ? AND f.quarter = ?
            ORDER BY p.rank
            LIMIT 20
        ''', (fund_id, quarter))
        holdings = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return {
            'fund': dict(fund),
            'quarter': quarter,
            'holdings': holdings
        }
    
    def format_html_report(self, report: Dict, report_type: str = 'daily') -> str:
        """Format report as HTML email"""
        if report_type == 'daily':
            return self._format_daily_html(report)
        elif report_type == 'fund':
            return self._format_fund_html(report)
        else:
            return "<p>Unknown report type</p>"
    
    def _format_daily_html(self, report: Dict) -> str:
        """Format daily report as HTML"""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #1a1a1a; border-bottom: 2px solid #4CAF50; padding-bottom: 10px; }}
        h2 {{ color: #333; margin-top: 30px; font-size: 18px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th {{ background: #f5f5f5; padding: 12px; text-align: left; font-weight: 600; font-size: 12px; text-transform: uppercase; }}
        td {{ padding: 12px; border-bottom: 1px solid #eee; }}
        .ticker {{ font-family: 'Courier New', monospace; font-weight: bold; color: #4CAF50; }}
        .value {{ text-align: right; }}
        .footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; color: #888; font-size: 12px; }}
        .header {{ background: #1a1a1a; color: white; padding: 30px; text-align: center; margin: -20px -20px 20px -20px; }}
        .header h1 {{ color: white; border: none; margin: 0; }}
        .header p {{ margin: 10px 0 0 0; opacity: 0.8; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🐋 13F Tracker</h1>
        <p>Daily Institutional Holdings Report - {report['date']}</p>
    </div>
"""
        
        # Recent Filings
        if report['recent_filings']:
            html += "<h2>📊 Recent 13F Filings</h2><table>"
            html += "<tr><th>Fund</th><th>Quarter</th><th>Filing Date</th><th>Value</th></tr>"
            for filing in report['recent_filings'][:5]:
                value = f"${filing['total_value']/1e9:.1f}B" if filing['total_value'] >= 1e9 else f"${filing['total_value']/1e6:.0f}M"
                html += f"<tr><td>{filing['name']}</td><td>{filing['quarter']}</td><td>{filing['filing_date']}</td><td class='value'>{value}</td></tr>"
            html += "</table>"
        
        # Consensus
        if report['consensus']:
            html += "<h2>🎯 Top Consensus Holdings</h2><table>"
            html += "<tr><th>Ticker</th><th>Funds Holding</th><th>Total Value</th><th>Avg Weight</th></tr>"
            for item in report['consensus'][:10]:
                value = f"${item['total_value']/1e6:.0f}M"
                html += f"<tr><td class='ticker'>{item['ticker']}</td><td>{item['fund_count']}</td><td class='value'>{value}</td><td class='value'>{item['avg_weight']:.1f}%</td></tr>"
            html += "</table>"
        
        # Top Positions
        if report['top_positions']:
            html += "<h2>🏆 Largest Positions</h2><table>"
            html += "<tr><th>Fund</th><th>Ticker</th><th>Value</th><th>Weight</th></tr>"
            for pos in report['top_positions'][:10]:
                value = f"${pos['value']/1e6:.0f}M"
                html += f"<tr><td>{pos['fund_name']}</td><td class='ticker'>{pos['ticker']}</td><td class='value'>{value}</td><td class='value'>{pos['portfolio_pct']:.1f}%</td></tr>"
            html += "</table>"
        
        html += f"""
    <div class="footer">
        <p>Track institutional smart money via SEC 13F filings</p>
        <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')} | <a href="https://github.com/josecookai/hedge-fund-13f-tracker">GitHub</a></p>
    </div>
</body>
</html>
"""
        return html
    
    def _format_fund_html(self, report: Dict) -> str:
        """Format fund report as HTML"""
        fund = report['fund']
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #1a1a1a; }}
        h2 {{ color: #333; margin-top: 30px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th {{ background: #f5f5f5; padding: 12px; text-align: left; }}
        td {{ padding: 12px; border-bottom: 1px solid #eee; }}
        .ticker {{ font-family: 'Courier New', monospace; font-weight: bold; color: #4CAF50; }}
        .header {{ background: #1a1a1a; color: white; padding: 30px; text-align: center; margin: -20px -20px 20px -20px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{fund['name']}</h1>
        <p>{report['quarter']} 13F Report | Manager: {fund['manager'] or 'Unknown'}</p>
    </div>
"""
        
        if report['holdings']:
            html += "<h2>Top Holdings</h2><table>"
            html += "<tr><th>Rank</th><th>Ticker</th><th>Company</th><th>Value</th><th>Weight</th></tr>"
            for h in report['holdings']:
                value = f"${h['value']/1e6:.1f}M"
                html += f"<tr><td>{h['rank']}</td><td class='ticker'>{h['ticker']}</td><td>{h['company_name'] or h['ticker']}</td><td>{value}</td><td>{h['portfolio_pct']:.1f}%</td></tr>"
            html += "</table>"
        
        html += """
    <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; color: #888; font-size: 12px;">
        <p>Track institutional smart money via SEC 13F filings</p>
    </div>
</body>
</html>
"""
        return html
    
    def send_email(self, to: str, subject: str, html_content: str, 
                   text_content: Optional[str] = None) -> bool:
        """Send email via Resend"""
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'from': self.from_email,
            'to': [to],
            'subject': subject,
            'html': html_content,
            'text': text_content or 'Please view this email in an HTML-capable client.'
        }
        
        try:
            response = requests.post(RESEND_API_URL, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            result = response.json()
            print(f"✅ Email sent: {result.get('id')}")
            return True
        except Exception as e:
            print(f"❌ Failed to send email: {e}")
            return False
    
    def send_daily_report(self, recipient: str) -> bool:
        """Send daily report to recipient"""
        report = self.generate_daily_report()
        html = self.format_html_report(report, 'daily')
        
        return self.send_email(
            to=recipient,
            subject=f"🐋 13F Tracker Daily Report - {report['date']}",
            html_content=html
        )
    
    def send_fund_report(self, recipient: str, fund_id: str, quarter: Optional[str] = None) -> bool:
        """Send fund-specific report"""
        report = self.generate_fund_report(fund_id, quarter)
        
        if not report:
            print(f"❌ Could not generate report for {fund_id}")
            return False
        
        html = self.format_html_report(report, 'fund')
        fund_name = report['fund']['name']
        
        return self.send_email(
            to=recipient,
            subject=f"📊 {fund_name} - {report['quarter']} Report",
            html_content=html
        )


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='13F Tracker Email Reports')
    parser.add_argument('--to', required=True, help='Recipient email address')
    parser.add_argument('--type', choices=['daily', 'fund'], default='daily', help='Report type')
    parser.add_argument('--fund', help='Fund ID (for fund report)')
    parser.add_argument('--quarter', help='Quarter (for fund report)')
    
    args = parser.parse_args()
    
    reporter = EmailReporter()
    
    print(f"📧 Generating {args.type} report for {args.to}\n")
    
    if args.type == 'daily':
        success = reporter.send_daily_report(args.to)
    elif args.type == 'fund':
        if not args.fund:
            print("❌ --fund required for fund report")
            return
        success = reporter.send_fund_report(args.to, args.fund, args.quarter)
    
    if success:
        print("\n✅ Report sent successfully")
    else:
        print("\n❌ Failed to send report")


if __name__ == '__main__':
    main()
