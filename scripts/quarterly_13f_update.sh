#!/bin/bash
# SEC 13F Bulk Data - Quarterly Cron Job
# Run: 0 0 15 2,5,8,11 * (15th of Feb, May, Aug, Nov)
# Or manually: ./quarterly_13f_update.sh

set -e

cd /root/clawd/hedge-fund-13f-tracker

echo "🐋 SEC 13F Quarterly Update - $(date)"
echo ""

# Determine current quarter
YEAR=$(date +%Y)
MONTH=$(date +%m)

if [ $MONTH -le 3 ]; then
    QUARTER="${YEAR}-Q1"
elif [ $MONTH -le 6 ]; then
    QUARTER="${YEAR}-Q2"
elif [ $MONTH -le 9 ]; then
    QUARTER="${YEAR}-Q3"
else
    QUARTER="${YEAR}-Q4"
fi

echo "📅 Quarter: $QUARTER"
echo ""

# Method 1: Simple wget (if SEC provides direct link)
echo "📥 Method 1: Attempting direct SEC download..."
mkdir -p data/sec_bulk

# Try to download (this URL format may vary)
FILE="13f-hr-${YEAR}-${QUARTER,,}.txt.gz"
URL="https://www.sec.gov/Archives/edgar/Feed/13F/${FILE}"

if wget --timeout=300 --tries=3 \
    --user-agent="HedgeFundTracker contact@example.com" \
    -O "data/sec_bulk/${FILE}" "$URL" 2>/dev/null; then
    
    echo "✅ Downloaded: data/sec_bulk/${FILE}"
    echo "   Size: $(du -h data/sec_bulk/${FILE} | cut -f1)"
    
    # Parse and import
    echo ""
    echo "📖 Parsing and importing..."
    python3 scripts/bulk_ingest.py --parse-only "data/sec_bulk/${FILE}"
    
else
    echo "⚠️  Direct download failed, using fallback..."
    
    # Method 2: Fallback to individual fund updates
    echo "📊 Updating individual funds..."
    
    FUNDS=(
        "tiger-global:0001167483"
        "situational-awareness:0002045724"
        "monolith-management:0001652044"
        "atreides-management:0001736297"
    )
    
    for fund_cik in "${FUNDS[@]}"; do
        IFS=':' read -r FUND CIK <<< "$fund_cik"
        echo "  Updating: $FUND"
        
        python3 scripts/ingest_filing.py \
            --fund "$FUND" \
            --quarter "$QUARTER" \
            --source sec 2>&1 | grep -E "(Imported|Error)" || true
        
        sleep 2  # Rate limit
    done
fi

echo ""
echo "✅ Quarterly update complete!"
echo "📊 Summary:"
python3 << 'PYEOF'
import sqlite3
conn = sqlite3.connect('data/tracker.db')
cursor = conn.cursor()

quarter = "${QUARTER}"
cursor.execute('''
    SELECT f.name, COUNT(p.id), SUM(p.value)
    FROM funds f
    JOIN filings fil ON f.id = fil.fund_id
    LEFT JOIN positions p ON fil.id = p.filing_id
    WHERE fil.quarter = ?
    GROUP BY f.id
''', (quarter,))

print(f"\nFunds with {quarter} data:")
for row in cursor.fetchall():
    value = f"${row[2]/1e9:.2f}B" if row[2] else "N/A"
    print(f"  {row[0][:30]:30} {row[1]:>3} positions  {value:>10}")

conn.close()
PYEOF

echo ""
echo "🕐 Next update: $(date -d '+3 months' '+%Y-%m-%d')"
