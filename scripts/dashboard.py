#!/usr/bin/env python3
"""
Web Dashboard - FastAPI backend for 13F Tracker
"""
import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn

DB_PATH = Path(__file__).parent.parent / 'data' / 'tracker.db'
TEMPLATES_DIR = Path(__file__).parent / 'templates'
STATIC_DIR = Path(__file__).parent / 'static'

# Create FastAPI app
app = FastAPI(
    title="Hedge Fund 13F Tracker",
    description="Monitor institutional investor holdings via SEC 13F filings",
    version="1.0.0"
)

# Create templates directory if not exists
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
STATIC_DIR.mkdir(parents=True, exist_ok=True)

# Setup templates
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def get_db():
    """Get database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ==================== API Endpoints ====================

@app.get("/api/funds")
def api_list_funds():
    """List all tracked funds"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT f.id, f.name, f.manager, f.strategy, f.aum, f.cik,
               COUNT(DISTINCT fil.id) as filing_count,
               MAX(fil.quarter) as latest_quarter
        FROM funds f
        LEFT JOIN filings fil ON f.id = fil.fund_id
        GROUP BY f.id
        ORDER BY f.aum DESC
    ''')
    
    funds = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return {"funds": funds, "count": len(funds)}


@app.get("/api/funds/{fund_id}")
def api_get_fund(fund_id: str):
    """Get fund details"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM funds WHERE id = ?', (fund_id,))
    fund = cursor.fetchone()
    
    if not fund:
        conn.close()
        raise HTTPException(status_code=404, detail="Fund not found")
    
    # Get filings
    cursor.execute('''
        SELECT * FROM filings 
        WHERE fund_id = ? 
        ORDER BY quarter DESC
    ''', (fund_id,))
    filings = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return {
        "fund": dict(fund),
        "filings": filings
    }


@app.get("/api/funds/{fund_id}/holdings")
def api_get_holdings(fund_id: str, quarter: Optional[str] = None):
    """Get fund holdings"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Check fund exists
    cursor.execute('SELECT * FROM funds WHERE id = ?', (fund_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Fund not found")
    
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
        raise HTTPException(status_code=404, detail="No filings found")
    
    # Get holdings
    cursor.execute('''
        SELECT p.*, f.total_value as fund_total
        FROM positions p
        JOIN filings f ON p.filing_id = f.id
        WHERE f.fund_id = ? AND f.quarter = ?
        ORDER BY p.rank
    ''', (fund_id, quarter))
    
    holdings = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return {
        "fund_id": fund_id,
        "quarter": quarter,
        "holdings": holdings,
        "count": len(holdings)
    }


@app.get("/api/funds/{fund_id}/changes")
def api_get_changes(fund_id: str, q1: str, q2: str):
    """Get changes between quarters"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Get positions for both quarters
    cursor.execute('''
        SELECT p.ticker, p.company_name, p.shares, p.value, p.portfolio_pct
        FROM positions p
        JOIN filings f ON p.filing_id = f.id
        WHERE f.fund_id = ? AND f.quarter = ?
    ''', (fund_id, q1))
    q1_positions = {p['ticker']: dict(p) for p in cursor.fetchall()}
    
    cursor.execute('''
        SELECT p.ticker, p.company_name, p.shares, p.value, p.portfolio_pct
        FROM positions p
        JOIN filings f ON p.filing_id = f.id
        WHERE f.fund_id = ? AND f.quarter = ?
    ''', (fund_id, q2))
    q2_positions = {p['ticker']: dict(p) for p in cursor.fetchall()}
    
    conn.close()
    
    # Analyze changes
    all_tickers = set(q1_positions.keys()) | set(q2_positions.keys())
    
    changes = {
        'NEW': [],
        'SOLD': [],
        'ADDED': [],
        'REDUCED': [],
        'UNCHANGED': []
    }
    
    for ticker in all_tickers:
        p1 = q1_positions.get(ticker)
        p2 = q2_positions.get(ticker)
        
        if not p1 and p2:
            changes['NEW'].append({
                'ticker': ticker,
                'company_name': p2['company_name'],
                'shares': p2['shares'],
                'value': p2['value']
            })
        elif p1 and not p2:
            changes['SOLD'].append({
                'ticker': ticker,
                'company_name': p1['company_name'],
                'previous_shares': p1['shares'],
                'previous_value': p1['value']
            })
        elif p1 and p2:
            share_change = p2['shares'] - p1['shares']
            change_pct = (share_change / p1['shares'] * 100) if p1['shares'] > 0 else 0
            
            if abs(change_pct) < 1:
                changes['UNCHANGED'].append({
                    'ticker': ticker,
                    'change_pct': change_pct
                })
            elif change_pct > 0:
                changes['ADDED'].append({
                    'ticker': ticker,
                    'change_pct': change_pct,
                    'previous_shares': p1['shares'],
                    'current_shares': p2['shares']
                })
            else:
                changes['REDUCED'].append({
                    'ticker': ticker,
                    'change_pct': change_pct,
                    'previous_shares': p1['shares'],
                    'current_shares': p2['shares']
                })
    
    return {
        "fund_id": fund_id,
        "q1": q1,
        "q2": q2,
        "changes": changes
    }


@app.get("/api/consensus")
def api_get_consensus(ticker: str):
    """Get consensus view for a ticker"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT f.name as fund_name, p.shares, p.value, p.portfolio_pct, p.rank, fil.quarter
        FROM positions p
        JOIN filings fil ON p.filing_id = fil.id
        JOIN funds f ON fil.fund_id = f.id
        WHERE p.ticker = ?
        ORDER BY p.value DESC
    ''', (ticker.upper(),))
    
    holdings = [dict(row) for row in cursor.fetchall()]
    
    # Calculate consensus metrics
    total_value = sum(h['value'] for h in holdings)
    avg_weight = sum(h['portfolio_pct'] for h in holdings) / len(holdings) if holdings else 0
    
    conn.close()
    
    return {
        "ticker": ticker.upper(),
        "funds_holding": len(holdings),
        "total_value": total_value,
        "avg_weight": avg_weight,
        "holdings": holdings
    }


@app.get("/api/heatmap")
def api_get_heatmap():
    """Get heatmap data for most held stocks"""
    conn = get_db()
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
        LIMIT 50
    ''')
    
    heatmap_data = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return {
        "stocks": heatmap_data,
        "count": len(heatmap_data)
    }


# ==================== Web Pages ====================

@app.get("/", response_class=HTMLResponse)
def page_home(request: Request):
    """Home page - fund overview"""
    conn = get_db()
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
    
    funds = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "funds": funds,
        "title": "Hedge Fund 13F Tracker"
    })


@app.get("/fund/{fund_id}", response_class=HTMLResponse)
def page_fund(request: Request, fund_id: str):
    """Fund detail page"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM funds WHERE id = ?', (fund_id,))
    fund = cursor.fetchone()
    
    if not fund:
        conn.close()
        raise HTTPException(status_code=404, detail="Fund not found")
    
    cursor.execute('''
        SELECT quarter FROM filings 
        WHERE fund_id = ? 
        ORDER BY quarter DESC
    ''', (fund_id,))
    quarters = [row['quarter'] for row in cursor.fetchall()]
    
    conn.close()
    
    return templates.TemplateResponse("fund.html", {
        "request": request,
        "fund": dict(fund),
        "quarters": quarters,
        "title": f"{fund['name']} - 13F Holdings"
    })


@app.get("/consensus", response_class=HTMLResponse)
def page_consensus(request: Request):
    """Consensus page"""
    return templates.TemplateResponse("consensus.html", {
        "request": request,
        "title": "Consensus Analysis"
    })


@app.get("/heatmap", response_class=HTMLResponse)
def page_heatmap(request: Request):
    """Heatmap page"""
    return templates.TemplateResponse("heatmap.html", {
        "request": request,
        "title": "Institutional Heatmap"
    })


# ==================== HTML Templates ====================

def create_templates():
    """Create default HTML templates if they don't exist"""
    
    # Base template
    base_html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}13F Tracker{% endblock %}</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0a0a0a; color: #e0e0e0; line-height: 1.6; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        header { background: #1a1a1a; padding: 20px 0; margin-bottom: 30px; border-bottom: 2px solid #333; }
        header h1 { color: #fff; font-size: 24px; }
        header nav { margin-top: 10px; }
        header nav a { color: #888; text-decoration: none; margin-right: 20px; }
        header nav a:hover { color: #fff; }
        .card { background: #1a1a1a; border-radius: 8px; padding: 20px; margin-bottom: 20px; }
        .card h2 { color: #fff; margin-bottom: 15px; font-size: 18px; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #333; }
        th { color: #888; font-weight: 500; font-size: 12px; text-transform: uppercase; }
        tr:hover { background: #252525; }
        .ticker { font-family: 'Courier New', monospace; font-weight: bold; color: #4CAF50; }
        .value { text-align: right; font-family: 'Courier New', monospace; }
        .positive { color: #4CAF50; }
        .negative { color: #f44336; }
        .neutral { color: #888; }
        .badge { padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: 500; }
        .badge-new { background: #4CAF50; color: #000; }
        .badge-sold { background: #f44336; color: #fff; }
        .badge-added { background: #2196F3; color: #fff; }
        .badge-reduced { background: #FF9800; color: #000; }
        footer { text-align: center; padding: 40px 0; color: #666; font-size: 12px; }
    </style>
    {% block extra_css %}{% endblock %}
</head>
<body>
    <header>
        <div class="container">
            <h1>🐋 Hedge Fund 13F Tracker</h1>
            <nav>
                <a href="/">Funds</a>
                <a href="/consensus">Consensus</a>
                <a href="/heatmap">Heatmap</a>
            </nav>
        </div>
    </header>
    
    <div class="container">
        {% block content %}{% endblock %}
    </div>
    
    <footer>
        <div class="container">
            Track institutional smart money via SEC 13F filings
        </div>
    </footer>
    
    {% block extra_js %}{% endblock %}
</body>
</html>'''
    
    # Index template
    index_html = '''{% extends "base.html" %}

{% block title %}Hedge Fund 13F Tracker{% endblock %}

{% block content %}
<div class="card">
    <h2>Tracked Hedge Funds</h2>
    <table>
        <thead>
            <tr>
                <th>Fund</th>
                <th>Manager</th>
                <th>AUM</th>
                <th>Latest Quarter</th>
                <th>Filings</th>
            </tr>
        </thead>
        <tbody>
            {% for fund in funds %}
            <tr>
                <td><a href="/fund/{{ fund.id }}">{{ fund.name }}</a></td>
                <td>{{ fund.manager or 'Unknown' }}</td>
                <td class="value">{% if fund.aum >= 1000000000 %}${{ "%.1f" | format(fund.aum/1000000000) }}B{% else %}${{ "%.0f" | format(fund.aum/1000000) }}M{% endif %}</td>
                <td>{{ fund.latest_quarter or 'N/A' }}</td>
                <td>{{ fund.filing_count }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>
{% endblock %}'''
    
    # Fund template
    fund_html = '''{% extends "base.html" %}

{% block title %}{{ fund.name }} - 13F Holdings{% endblock %}

{% block content %}
<div class="card">
    <h2>{{ fund.name }}</h2>
    <p>Manager: {{ fund.manager or 'Unknown' }} | AUM: {% if fund.aum >= 1000000000 %}${{ "%.1f" | format(fund.aum/1000000000) }}B{% else %}${{ "%.0f" | format(fund.aum/1000000) }}M{% endif %}</p>
    
    <div style="margin: 20px 0;">
        <label>Quarter: </label>
        <select id="quarter-select">
            {% for q in quarters %}
            <option value="{{ q }}">{{ q }}</option>
            {% endfor %}
        </select>
    </div>
</div>

<div class="card">
    <h2>Holdings</h2>
    <div id="holdings-table">Loading...</div>
</div>

{% if quarters|length >= 2 %}
<div class="card">
    <h2>Changes ({{ quarters[1] }} → {{ quarters[0] }})</h2>
    <div id="changes-table">Loading...</div>
</div>
{% endif %}

{% block extra_js %}
<script>
const fundId = '{{ fund.id }}';
const quarters = {{ quarters | tojson }};

async function loadHoldings(quarter) {
    const res = await fetch(`/api/funds/${fundId}/holdings?quarter=${quarter}`);
    const data = await res.json();
    
    let html = '<table><thead><tr><th>Rank</th><th>Ticker</th><th>Company</th><th>Shares</th><th>Value</th><th>Weight</th></tr></thead><tbody>';
    
    data.holdings.forEach(h => {
        const shares = h.shares >= 1000000 ? (h.shares/1000000).toFixed(2) + 'M' : (h.shares/1000).toFixed(0) + 'K';
        const value = h.value >= 1000000000 ? '$' + (h.value/1000000000).toFixed(1) + 'B' : '$' + (h.value/1000000).toFixed(1) + 'M';
        html += `<tr><td>${h.rank}</td><td class="ticker">${h.ticker}</td><td>${h.company_name || h.ticker}</td><td class="value">${shares}</td><td class="value">${value}</td><td class="value">${h.portfolio_pct.toFixed(1)}%</td></tr>`;
    });
    
    html += '</tbody></table>';
    document.getElementById('holdings-table').innerHTML = html;
}

async function loadChanges() {
    if (quarters.length < 2) return;
    const res = await fetch(`/api/funds/${fundId}/changes?q1=${quarters[1]}&q2=${quarters[0]}`);
    const data = await res.json();
    
    let html = '';
    
    if (data.changes.NEW.length > 0) {
        html += '<h3>🆕 New Positions</h3><table><thead><tr><th>Ticker</th><th>Company</th><th>Value</th></tr></thead><tbody>';
        data.changes.NEW.forEach(c => {
            const value = c.value >= 1000000 ? '$' + (c.value/1000000).toFixed(1) + 'M' : '$' + (c.value/1000).toFixed(0) + 'K';
            html += `<tr><td class="ticker">${c.ticker}</td><td>${c.company_name || c.ticker}</td><td class="value">${value}</td></tr>`;
        });
        html += '</tbody></table>';
    }
    
    if (data.changes.SOLD.length > 0) {
        html += '<h3>❌ Sold Out</h3><table><thead><tr><th>Ticker</th><th>Company</th><th>Previous Value</th></tr></thead><tbody>';
        data.changes.SOLD.forEach(c => {
            const value = c.previous_value >= 1000000 ? '$' + (c.previous_value/1000000).toFixed(1) + 'M' : '$' + (c.previous_value/1000).toFixed(0) + 'K';
            html += `<tr><td class="ticker">${c.ticker}</td><td>${c.company_name || c.ticker}</td><td class="value">${value}</td></tr>`;
        });
        html += '</tbody></table>';
    }
    
    document.getElementById('changes-table').innerHTML = html || '<p>No significant changes</p>';
}

document.getElementById('quarter-select').addEventListener('change', (e) => {
    loadHoldings(e.target.value);
});

// Initial load
if (quarters.length > 0) {
    loadHoldings(quarters[0]);
    loadChanges();
}
</script>
{% endblock %}
{% endblock %}'''
    
    # Consensus template
    consensus_html = '''{% extends "base.html" %}

{% block title %}Consensus Analysis - 13F Tracker{% endblock %}

{% block content %}
<div class="card">
    <h2>Consensus Analysis</h2>
    <p>Enter a ticker to see which hedge funds hold it</p>
    
    <div style="margin: 20px 0;">
        <input type="text" id="ticker-input" placeholder="e.g., NVDA" style="padding: 10px; font-size: 16px; background: #252525; border: 1px solid #333; color: #fff; border-radius: 4px;">
        <button onclick="loadConsensus()" style="padding: 10px 20px; margin-left: 10px; background: #4CAF50; color: #000; border: none; border-radius: 4px; cursor: pointer; font-weight: bold;">Search</button>
    </div>
</div>

<div class="card" id="results" style="display: none;">
    <h2 id="result-title"></h2>
    <div id="result-content"></div>
</div>

{% block extra_js %}
<script>
async function loadConsensus() {
    const ticker = document.getElementById('ticker-input').value.toUpperCase();
    if (!ticker) return;
    
    const res = await fetch(`/api/consensus?ticker=${ticker}`);
    const data = await res.json();
    
    document.getElementById('result-title').textContent = `${data.ticker} - ${data.funds_holding} Funds Holding`;
    
    let html = `<p>Total Value: $${(data.total_value/1000000).toFixed(1)}M | Average Weight: ${data.avg_weight.toFixed(1)}%</p>`;
    
    html += '<table><thead><tr><th>Fund</th><th>Quarter</th><th>Shares</th><th>Value</th><th>Weight</th></tr></thead><tbody>';
    
    data.holdings.forEach(h => {
        const shares = h.shares >= 1000000 ? (h.shares/1000000).toFixed(2) + 'M' : (h.shares/1000).toFixed(0) + 'K';
        const value = h.value >= 1000000000 ? '$' + (h.value/1000000000).toFixed(1) + 'B' : '$' + (h.value/1000000).toFixed(1) + 'M';
        html += `<tr><td>${h.fund_name}</td><td>${h.quarter}</td><td class="value">${shares}</td><td class="value">${value}</td><td class="value">${h.portfolio_pct.toFixed(1)}%</td></tr>`;
    });
    
    html += '</tbody></table>';
    
    document.getElementById('result-content').innerHTML = html;
    document.getElementById('results').style.display = 'block';
}

document.getElementById('ticker-input').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') loadConsensus();
});
</script>
{% endblock %}
{% endblock %}'''
    
    # Heatmap template
    heatmap_html = '''{% extends "base.html" %}

{% block title %}Institutional Heatmap - 13F Tracker{% endblock %}

{% block content %}
<div class="card">
    <h2>Institutional Heatmap</h2>
    <p>Most held stocks across tracked hedge funds</p>
</div>

<div class="card">
    <div id="heatmap-table">Loading...</div>
</div>

{% block extra_js %}
<script>
async function loadHeatmap() {
    const res = await fetch('/api/heatmap');
    const data = await res.json();
    
    let html = '<table><thead><tr><th>Ticker</th><th>Funds Holding</th><th>Total Value</th><th>Avg Weight</th></tr></thead><tbody>';
    
    data.stocks.forEach(s => {
        const value = s.total_value >= 1000000000 ? '$' + (s.total_value/1000000000).toFixed(1) + 'B' : '$' + (s.total_value/1000000).toFixed(1) + 'M';
        html += `<tr><td class="ticker">${s.ticker}</td><td>${s.fund_count}</td><td class="value">${value}</td><td class="value">${s.avg_weight.toFixed(1)}%</td></tr>`;
    });
    
    html += '</tbody></table>';
    document.getElementById('heatmap-table').innerHTML = html;
}

loadHeatmap();
</script>
{% endblock %}
{% endblock %}'''
    
    # Write templates
    templates = {
        'base.html': base_html,
        'index.html': index_html,
        'fund.html': fund_html,
        'consensus.html': consensus_html,
        'heatmap.html': heatmap_html
    }
    
    for name, content in templates.items():
        path = TEMPLATES_DIR / name
        if not path.exists():
            path.write_text(content)
            print(f"Created template: {name}")


@app.on_event("startup")
def startup_event():
    """Create templates on startup"""
    create_templates()


def main():
    """Run the web server"""
    print("🐋 Starting Hedge Fund 13F Tracker Dashboard")
    print("📊 API: http://localhost:8000/api")
    print("🌐 Web: http://localhost:8000")
    print("\nPress Ctrl+C to stop\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == '__main__':
    main()
