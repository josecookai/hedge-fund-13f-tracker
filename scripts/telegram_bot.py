#!/usr/bin/env python3
"""
Telegram Bot for 13F Tracker
Commands: /funds, /holdings, /alerts, /consensus, /addfund
"""
import sqlite3
import json
import asyncio
from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass

# For actual Telegram Bot API integration, you would use python-telegram-bot
# This is a skeleton implementation that can be integrated with the real bot

try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    print("python-telegram-bot not installed. Run: pip install python-telegram-bot")

DB_PATH = Path(__file__).parent.parent / 'data' / 'tracker.db'


@dataclass
class AlertConfig:
    """User alert configuration"""
    user_id: int
    fund_id: Optional[str]
    ticker: Optional[str]
    alert_types: List[str]  # NEW, SOLD, ADDED, REDUCED
    min_value: int  # Minimum dollar value to alert


class Tracker13FBot:
    """Telegram Bot for 13F Tracker"""
    
    def __init__(self, token: str, db_path: Path = DB_PATH):
        self.token = token
        self.db_path = db_path
        self.application = None
        if TELEGRAM_AVAILABLE:
            self.application = Application.builder().token(token).build()
            self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup command handlers"""
        self.application.add_handler(CommandHandler("start", self.cmd_start))
        self.application.add_handler(CommandHandler("help", self.cmd_help))
        self.application.add_handler(CommandHandler("funds", self.cmd_funds))
        self.application.add_handler(CommandHandler("holdings", self.cmd_holdings))
        self.application.add_handler(CommandHandler("alerts", self.cmd_alerts))
        self.application.add_handler(CommandHandler("consensus", self.cmd_consensus))
        self.application.add_handler(CommandHandler("compare", self.cmd_compare))
        self.application.add_handler(CommandHandler("heatmap", self.cmd_heatmap))
    
    def get_db(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start command"""
        welcome_message = """
🐋 **Hedge Fund 13F Tracker Bot**

Track institutional "smart money" positions via SEC 13F filings.

**Commands:**
/funds - List tracked hedge funds
/holdings <fund> - Show fund holdings
/compare <fund> <q1> <q2> - Compare quarters
/consensus <ticker> - See who holds a stock
/heatmap - Most held stocks
/alerts - Manage your alerts
/help - Show this help message

Example:
`/holdings atreides-management`
`/consensus NVDA`
`/compare atreides-management 2024-Q3 2024-Q4`
        """
        await update.message.reply_text(welcome_message, parse_mode='Markdown')
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Help command"""
        await self.cmd_start(update, context)
    
    async def cmd_funds(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """List tracked funds"""
        conn = self.get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT f.id, f.name, f.manager, f.aum,
                   COUNT(DISTINCT fil.id) as filing_count,
                   MAX(fil.quarter) as latest_quarter
            FROM funds f
            LEFT JOIN filings fil ON f.id = fil.fund_id
            GROUP BY f.id
            ORDER BY f.aum DESC
        ''')
        
        funds = cursor.fetchall()
        conn.close()
        
        message = "🐋 **Tracked Hedge Funds**\n\n"
        for fund in funds:
            aum = f"${fund['aum']/1e9:.1f}B" if fund['aum'] and fund['aum'] >= 1e9 else f"${fund['aum']/1e6:.0f}M"
            message += f"• **{fund['name']}**\n"
            message += f"  Manager: {fund['manager'] or 'Unknown'}\n"
            message += f"  AUM: {aum} | Latest: {fund['latest_quarter'] or 'N/A'}\n\n"
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def cmd_holdings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show fund holdings"""
        if not context.args:
            await update.message.reply_text(
                "Usage: /holdings <fund_id> [quarter]\n"
                "Example: /holdings atreides-management 2024-Q4",
                parse_mode='Markdown'
            )
            return
        
        fund_id = context.args[0]
        quarter = context.args[1] if len(context.args) > 1 else None
        
        conn = self.get_db()
        cursor = conn.cursor()
        
        # Get fund info
        cursor.execute('SELECT * FROM funds WHERE id = ?', (fund_id,))
        fund = cursor.fetchone()
        
        if not fund:
            conn.close()
            await update.message.reply_text(f"❌ Fund not found: {fund_id}")
            return
        
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
            await update.message.reply_text(f"❌ No filings found for {fund_id}")
            return
        
        # Get top 10 holdings
        cursor.execute('''
            SELECT p.*
            FROM positions p
            JOIN filings f ON p.filing_id = f.id
            WHERE f.fund_id = ? AND f.quarter = ?
            ORDER BY p.rank
            LIMIT 10
        ''', (fund_id, quarter))
        
        holdings = cursor.fetchall()
        conn.close()
        
        aum_str = f"${fund['aum']/1e9:.1f}B" if fund['aum'] and fund['aum'] >= 1e9 else f"${fund['aum']/1e6:.0f}M"
        
        message = f"📊 **{fund['name']}** - {quarter}\n"
        message += f"AUM: {aum_str} | Manager: {fund['manager'] or 'Unknown'}\n\n"
        message += "**Top 10 Holdings:**\n"
        
        for h in holdings:
            value_str = f"${h['value']/1e6:.1f}M" if h['value'] >= 1e6 else f"${h['value']/1e3:.0f}K"
            message += f"{h['rank']}. **{h['ticker']}** - {value_str} ({h['portfolio_pct']:.1f}%)\n"
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def cmd_compare(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Compare quarters"""
        if len(context.args) < 3:
            await update.message.reply_text(
                "Usage: /compare <fund_id> <q1> <q2>\n"
                "Example: /compare atreides-management 2024-Q3 2024-Q4",
                parse_mode='Markdown'
            )
            return
        
        fund_id = context.args[0]
        q1 = context.args[1]
        q2 = context.args[2]
        
        conn = self.get_db()
        cursor = conn.cursor()
        
        # Get positions for both quarters
        cursor.execute('''
            SELECT p.ticker, p.company_name, p.shares, p.value
            FROM positions p
            JOIN filings f ON p.filing_id = f.id
            WHERE f.fund_id = ? AND f.quarter = ?
        ''', (fund_id, q1))
        q1_positions = {p['ticker']: p for p in cursor.fetchall()}
        
        cursor.execute('''
            SELECT p.ticker, p.company_name, p.shares, p.value
            FROM positions p
            JOIN filings f ON p.filing_id = f.id
            WHERE f.fund_id = ? AND f.quarter = ?
        ''', (fund_id, q2))
        q2_positions = {p['ticker']: p for p in cursor.fetchall()}
        
        conn.close()
        
        # Analyze changes
        all_tickers = set(q1_positions.keys()) | set(q2_positions.keys())
        
        new_positions = []
        sold_positions = []
        added = []
        reduced = []
        
        for ticker in all_tickers:
            p1 = q1_positions.get(ticker)
            p2 = q2_positions.get(ticker)
            
            if not p1 and p2:
                new_positions.append(p2)
            elif p1 and not p2:
                sold_positions.append(p1)
            elif p1 and p2:
                change_pct = (p2['shares'] - p1['shares']) / p1['shares'] * 100
                if change_pct >= 20:
                    added.append((ticker, change_pct))
                elif change_pct <= -20:
                    reduced.append((ticker, change_pct))
        
        message = f"📈 **{fund_id}**: {q1} → {q2}\n\n"
        
        if new_positions:
            message += "🆕 **New Positions:**\n"
            for p in new_positions[:5]:
                value_str = f"${p['value']/1e6:.1f}M"
                message += f"• {p['ticker']} ({p['company_name'][:20]}) - {value_str}\n"
            message += "\n"
        
        if sold_positions:
            message += "❌ **Sold Out:**\n"
            for p in sold_positions[:5]:
                value_str = f"${p['value']/1e6:.1f}M"
                message += f"• {p['ticker']} - was {value_str}\n"
            message += "\n"
        
        if added:
            message += "📈 **Added:**\n"
            for ticker, pct in added:
                message += f"• {ticker}: +{pct:.1f}%\n"
            message += "\n"
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def cmd_consensus(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show consensus for ticker"""
        if not context.args:
            await update.message.reply_text(
                "Usage: /consensus <ticker>\n"
                "Example: /consensus NVDA",
                parse_mode='Markdown'
            )
            return
        
        ticker = context.args[0].upper()
        
        conn = self.get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT f.name as fund_name, p.shares, p.value, p.portfolio_pct, fil.quarter
            FROM positions p
            JOIN filings fil ON p.filing_id = fil.id
            JOIN funds f ON fil.fund_id = f.id
            WHERE p.ticker = ?
            ORDER BY p.value DESC
        ''', (ticker,))
        
        holdings = cursor.fetchall()
        conn.close()
        
        if not holdings:
            await update.message.reply_text(f"❌ No funds hold {ticker}")
            return
        
        total_value = sum(h['value'] for h in holdings)
        avg_weight = sum(h['portfolio_pct'] for h in holdings) / len(holdings)
        
        message = f"🎯 **{ticker}** - Institutional Holdings\n\n"
        message += f"{len(holdings)} funds holding ${total_value/1e6:.1f}M total\n"
        message += f"Average weight: {avg_weight:.1f}%\n\n"
        
        message += "**Top Holders:**\n"
        for h in holdings:
            value_str = f"${h['value']/1e6:.1f}M"
            message += f"• {h['fund_name'][:25]}: {value_str} ({h['portfolio_pct']:.1f}%)\n"
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def cmd_heatmap(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show heatmap"""
        conn = self.get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT p.ticker, COUNT(DISTINCT fil.fund_id) as fund_count,
                   SUM(p.value) as total_value,
                   AVG(p.portfolio_pct) as avg_weight
            FROM positions p
            JOIN filings fil ON p.filing_id = fil.id
            GROUP BY p.ticker
            HAVING fund_count >= 2
            ORDER BY fund_count DESC, total_value DESC
            LIMIT 15
        ''')
        
        heatmap = cursor.fetchall()
        conn.close()
        
        message = "🔥 **Institutional Heatmap**\n\n"
        message += "Most held stocks across tracked funds:\n\n"
        
        for i, row in enumerate(heatmap, 1):
            value_str = f"${row['total_value']/1e6:.0f}M"
            message += f"{i}. **{row['ticker']}** - {row['fund_count']} funds, {value_str} avg {row['avg_weight']:.1f}%\n"
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def cmd_alerts(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manage alerts"""
        message = """
🔔 **Alert Management**

Subscribe to get notified when:
• 🆕 New positions are added
• ❌ Positions are sold out
• 📈 Holdings increase >20%
• 📉 Holdings decrease >20%

**Coming Soon:**
• `/alert subscribe <fund>` - Subscribe to fund alerts
• `/alert subscribe <ticker>` - Subscribe to ticker alerts
• `/alert list` - List your subscriptions
• `/alert unsubscribe` - Unsubscribe from alerts

For now, check changes manually with:
`/compare <fund> <q1> <q2>`
        """
        await update.message.reply_text(message, parse_mode='Markdown')
    
    def run(self):
        """Start the bot"""
        if not TELEGRAM_AVAILABLE:
            print("❌ python-telegram-bot not installed")
            print("Install with: pip install python-telegram-bot")
            return
        
        print("🤖 Starting 13F Tracker Telegram Bot...")
        print("Press Ctrl+C to stop")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)


# Standalone alert sender (can be used by cron jobs)
def send_alert_to_telegram(bot_token: str, chat_id: str, alert_message: str):
    """Send alert message to Telegram"""
    try:
        import requests
        
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': alert_message,
            'parse_mode': 'Markdown',
            'disable_web_page_preview': True
        }
        
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        
        return response.json()
    except Exception as e:
        print(f"Failed to send Telegram alert: {e}")
        return None


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='13F Tracker Telegram Bot')
    parser.add_argument('--token', required=True, help='Telegram Bot Token')
    parser.add_argument('--send-alert', help='Send one-time alert message')
    parser.add_argument('--chat-id', help='Chat ID for alert')
    
    args = parser.parse_args()
    
    if args.send_alert and args.chat_id:
        # Send one-time alert
        result = send_alert_to_telegram(args.token, args.chat_id, args.send_alert)
        if result and result.get('ok'):
            print("✅ Alert sent successfully")
        else:
            print("❌ Failed to send alert")
    else:
        # Start bot
        bot = Tracker13FBot(args.token)
        bot.run()


if __name__ == '__main__':
    main()
