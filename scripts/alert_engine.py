#!/usr/bin/env python3
"""
Alert Engine - Detect position changes and generate alerts
Supports: NEW, SOLD, ADDED, REDUCED detection
"""
import sqlite3
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

DB_PATH = Path(__file__).resolve().parent.parent / 'data' / 'tracker.db'


@dataclass
class PositionChange:
    """Represents a change in position between quarters"""
    fund_id: str
    fund_name: str
    ticker: str
    company_name: str
    quarter: str
    previous_shares: int
    current_shares: int
    previous_value: int
    current_value: int
    change_pct: float
    activity: str  # NEW, SOLD, ADDED, REDUCED, UNCHANGED
    
    def to_dict(self) -> Dict:
        return {
            'fund_id': self.fund_id,
            'fund_name': self.fund_name,
            'ticker': self.ticker,
            'company_name': self.company_name,
            'quarter': self.quarter,
            'previous_shares': self.previous_shares,
            'current_shares': self.current_shares,
            'previous_value': self.previous_value,
            'current_value': self.current_value,
            'change_pct': self.change_pct,
            'activity': self.activity
        }


class AlertEngine:
    """Detect and manage position changes"""
    
    # Alert thresholds
    ADDED_THRESHOLD = 20.0  # 20% increase
    REDUCED_THRESHOLD = -20.0  # 20% decrease
    
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.conn = None
    
    def connect(self):
        """Connect to database"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
    
    def detect_changes(self, fund_id: str, q1: str, q2: str) -> List[PositionChange]:
        """
        Detect position changes between two quarters
        
        Returns list of PositionChange objects
        """
        cursor = self.conn.cursor()
        
        # Get fund name
        cursor.execute('SELECT name FROM funds WHERE id = ?', (fund_id,))
        fund_row = cursor.fetchone()
        fund_name = fund_row['name'] if fund_row else fund_id
        
        # Get positions for both quarters
        cursor.execute('''
            SELECT p.ticker, p.company_name, p.shares, p.value, p.portfolio_pct, p.rank
            FROM positions p
            JOIN filings f ON p.filing_id = f.id
            WHERE f.fund_id = ? AND f.quarter = ?
        ''', (fund_id, q1))
        q1_positions = {p['ticker']: p for p in cursor.fetchall()}
        
        cursor.execute('''
            SELECT p.ticker, p.company_name, p.shares, p.value, p.portfolio_pct, p.rank
            FROM positions p
            JOIN filings f ON p.filing_id = f.id
            WHERE f.fund_id = ? AND f.quarter = ?
        ''', (fund_id, q2))
        q2_positions = {p['ticker']: p for p in cursor.fetchall()}
        
        changes = []
        all_tickers = set(q1_positions.keys()) | set(q2_positions.keys())
        
        for ticker in all_tickers:
            p1 = q1_positions.get(ticker)
            p2 = q2_positions.get(ticker)
            
            if not p1 and p2:
                # NEW position
                changes.append(PositionChange(
                    fund_id=fund_id,
                    fund_name=fund_name,
                    ticker=ticker,
                    company_name=p2['company_name'] or ticker,
                    quarter=q2,
                    previous_shares=0,
                    current_shares=p2['shares'],
                    previous_value=0,
                    current_value=p2['value'],
                    change_pct=float('inf'),
                    activity='NEW'
                ))
            elif p1 and not p2:
                # SOLD position
                changes.append(PositionChange(
                    fund_id=fund_id,
                    fund_name=fund_name,
                    ticker=ticker,
                    company_name=p1['company_name'] or ticker,
                    quarter=q2,
                    previous_shares=p1['shares'],
                    current_shares=0,
                    previous_value=p1['value'],
                    current_value=0,
                    change_pct=float('-inf'),
                    activity='SOLD'
                ))
            elif p1 and p2:
                # Both quarters have position - calculate change
                share_change = p2['shares'] - p1['shares']
                change_pct = (share_change / p1['shares'] * 100) if p1['shares'] > 0 else 0
                
                # Determine activity
                if abs(change_pct) < 1:
                    activity = 'UNCHANGED'
                elif change_pct >= self.ADDED_THRESHOLD:
                    activity = 'ADDED'
                elif change_pct <= self.REDUCED_THRESHOLD:
                    activity = 'REDUCED'
                else:
                    activity = 'UNCHANGED'
                
                if activity != 'UNCHANGED':
                    changes.append(PositionChange(
                        fund_id=fund_id,
                        fund_name=fund_name,
                        ticker=ticker,
                        company_name=p2['company_name'] or p1['company_name'] or ticker,
                        quarter=q2,
                        previous_shares=p1['shares'],
                        current_shares=p2['shares'],
                        previous_value=p1['value'],
                        current_value=p2['value'],
                        change_pct=change_pct,
                        activity=activity
                    ))
        
        # Sort by activity priority and value
        activity_priority = {'NEW': 0, 'SOLD': 1, 'ADDED': 2, 'REDUCED': 3, 'UNCHANGED': 4}
        changes.sort(key=lambda x: (activity_priority.get(x.activity, 5), -x.current_value))
        
        return changes
    
    def save_changes(self, changes: List[PositionChange]) -> int:
        """Save detected changes to database"""
        cursor = self.conn.cursor()
        
        saved = 0
        for change in changes:
            change_id = f"{change.fund_id}-{change.quarter}-{change.ticker}"
            
            cursor.execute('''
                INSERT OR REPLACE INTO position_changes
                (id, fund_id, ticker, quarter, previous_shares, current_shares, change_pct, activity)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                change_id,
                change.fund_id,
                change.ticker,
                change.quarter,
                change.previous_shares,
                change.current_shares,
                change.change_pct,
                change.activity
            ))
            saved += 1
        
        self.conn.commit()
        return saved
    
    def get_significant_changes(self, fund_id: Optional[str] = None, 
                               quarter: Optional[str] = None,
                               min_value: int = 10_000_000) -> List[PositionChange]:
        """
        Get significant changes that warrant alerts
        
        Filters by minimum dollar value and activity type
        """
        cursor = self.conn.cursor()
        
        query = '''
            SELECT pc.*, f.name as fund_name, p.company_name
            FROM position_changes pc
            JOIN funds f ON pc.fund_id = f.id
            LEFT JOIN positions p ON pc.ticker = p.ticker
            WHERE pc.activity IN ('NEW', 'SOLD', 'ADDED', 'REDUCED')
            AND (p.value >= ? OR p.value IS NULL)
        '''
        params = [min_value]
        
        if fund_id:
            query += ' AND pc.fund_id = ?'
            params.append(fund_id)
        
        if quarter:
            query += ' AND pc.quarter = ?'
            params.append(quarter)
        
        query += ' ORDER BY pc.quarter DESC, p.value DESC NULLS LAST'
        
        cursor.execute(query, params)
        
        changes = []
        for row in cursor.fetchall():
            changes.append(PositionChange(
                fund_id=row['fund_id'],
                fund_name=row['fund_name'],
                ticker=row['ticker'],
                company_name=row['company_name'] or row['ticker'],
                quarter=row['quarter'],
                previous_shares=row['previous_shares'],
                current_shares=row['current_shares'],
                previous_value=0,  # Not stored in position_changes table
                current_value=0,
                change_pct=row['change_pct'],
                activity=row['activity']
            ))
        
        return changes
    
    def generate_alert_message(self, change: PositionChange) -> str:
        """Generate human-readable alert message"""
        emoji_map = {
            'NEW': '🆕',
            'SOLD': '❌',
            'ADDED': '📈',
            'REDUCED': '📉',
            'UNCHANGED': '➡️'
        }
        
        emoji = emoji_map.get(change.activity, '🔔')
        
        if change.activity == 'NEW':
            return f"{emoji} NEW: {change.fund_name} → {change.ticker} ({change.company_name}) - ${change.current_value/1e6:.1f}M"
        elif change.activity == 'SOLD':
            return f"{emoji} SOLD: {change.fund_name} → {change.ticker} ({change.company_name}) - was ${change.previous_value/1e6:.1f}M"
        elif change.activity == 'ADDED':
            return f"{emoji} ADDED: {change.fund_name} → {change.ticker} +{change.change_pct:.1f}% ({change.previous_shares/1e3:.0f}K → {change.current_shares/1e3:.0f}K shares)"
        elif change.activity == 'REDUCED':
            return f"{emoji} REDUCED: {change.fund_name} → {change.ticker} {change.change_pct:.1f}% ({change.previous_shares/1e3:.0f}K → {change.current_shares/1e3:.0f}K shares)"
        else:
            return f"{emoji} {change.activity}: {change.fund_name} → {change.ticker}"
    
    def export_changes_json(self, changes: List[PositionChange], filepath: str):
        """Export changes to JSON file"""
        data = {
            'generated_at': datetime.now().isoformat(),
            'total_changes': len(changes),
            'changes': [c.to_dict() for c in changes]
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        return filepath


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Alert Engine for 13F Tracker')
    parser.add_argument('--fund', '-f', help='Fund ID to analyze')
    parser.add_argument('--q1', help='First quarter (e.g., 2024-Q3)')
    parser.add_argument('--q2', help='Second quarter (e.g., 2024-Q4)')
    parser.add_argument('--save', action='store_true', help='Save changes to database')
    parser.add_argument('--export', help='Export changes to JSON file')
    parser.add_argument('--min-value', type=int, default=10_000_000, 
                       help='Minimum dollar value for alerts (default: 10M)')
    
    args = parser.parse_args()
    
    engine = AlertEngine()
    engine.connect()
    
    try:
        if args.fund and args.q1 and args.q2:
            # Detect changes between specific quarters
            print(f"🔍 Analyzing {args.fund}: {args.q1} → {args.q2}\n")
            
            changes = engine.detect_changes(args.fund, args.q1, args.q2)
            
            # Filter by minimum value
            significant = [c for c in changes 
                          if c.current_value >= args.min_value or c.previous_value >= args.min_value]
            
            print(f"Found {len(changes)} total changes, {len(significant)} significant\n")
            
            # Group by activity
            for activity in ['NEW', 'SOLD', 'ADDED', 'REDUCED']:
                activity_changes = [c for c in significant if c.activity == activity]
                if activity_changes:
                    print(f"\n{activity} ({len(activity_changes)}):")
                    for change in activity_changes:
                        print(f"  {engine.generate_alert_message(change)}")
            
            if args.save:
                saved = engine.save_changes(changes)
                print(f"\n💾 Saved {saved} changes to database")
            
            if args.export:
                engine.export_changes_json(significant, args.export)
                print(f"\n📁 Exported to {args.export}")
        
        else:
            # Show recent significant changes
            print("📊 Recent Significant Changes\n")
            changes = engine.get_significant_changes(min_value=args.min_value)
            
            if not changes:
                print("No significant changes found")
            else:
                for change in changes[:20]:
                    print(engine.generate_alert_message(change))
    
    finally:
        engine.close()


if __name__ == '__main__':
    main()
