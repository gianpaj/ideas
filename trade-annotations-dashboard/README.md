# Trade Annotations Dashboard

Automated system to visualize Lightyear trades on TradingView charts. Reads your weekly trade exports and uses Pine Script to draw buy/sell markers at exact price levels with order details.

## Problem

- Lightyear has no API to export trades to TradingView
- Manual chart annotation is tedious and error-prone
- Need weekly updates to reflect latest trades
- Want to track entry/exit prices visually on TradingView charts

## Solution

**3-tier architecture:**

### 1. API Server (Node.js)
- Parses Lightyear CSV exports
- Serves trades as JSON via simple REST endpoint
- Runs locally or on a lightweight server
- Auto-updates when CSV is replaced in a watched folder

**Endpoint:** `GET /api/trades`
```json
[
  {"date": "2026-03-12T14:58:05Z", "ticker": "FIG", "type": "BUY", "price": 27.00, "qty": 3, "ccy": "USD"},
  {"date": "2026-03-10T19:56:04Z", "ticker": "RBLX", "type": "BUY", "price": 58.94, "qty": 2, "ccy": "USD"},
  {"date": "2026-03-10T13:30:01Z", "ticker": "CRCL", "type": "SELL", "price": 113.60, "qty": 4, "ccy": "USD"}
]
```

### 2. Pine Script (TradingView Native)
- Deployed to TradingView public script library
- Fetches trades from API at chart refresh
- Filters by current chart symbol
- Draws markers:
  - **BUY:** Green upward arrow at entry price, labeled "BUY 3 @ $27.00"
  - **SELL:** Red downward arrow at exit price, labeled "SELL 4 @ $113.60"
- Includes timestamp in label
- Auto-hides duplicate entries (idempotent)

### 3. Update Workflow
**Weekly/biweekly manual step:**
1. Download Lightyear statement as CSV
2. Upload to API folder (or drag into a specific directory)
3. API auto-parses it
4. Open any TradingView chart → annotations appear instantly

## Data Format

**Input:** Lightyear CSV
```csv
"Date","Reference","Ticker","Type","Quantity","Price/share","Net Amt."
"12/03/2026 14:58:05","OR-5F3K6RWAY2","FIGl","Buy","3.000000000","27.000000000","81.00"
```

**Output:** JSON for Pine Script
```json
{
  "ticker": "FIG",
  "type": "BUY",
  "price": 27.0,
  "qty": 3,
  "date": "2026-03-12T14:58:05Z"
}
```

## Tech Stack

- **API:** Node.js + Express
- **CSV Parser:** `csv-parse`
- **Pine Script:** v5 (TradingView native)
- **Hosting:** Local or small VPS

## Data Flow

```
Lightyear CSV 
    ↓
[Weekly Upload]
    ↓
API Server (Node.js)
    ↓ Parses & Transforms
    ↓
JSON Endpoint (/api/trades)
    ↓
[Chart Refresh]
    ↓
Pine Script (TradingView)
    ↓ Fetches & Filters by Symbol
    ↓
Draw Markers on Chart
```

## Features

✅ Automatic marker placement at exact buy/sell prices  
✅ Labeled entries with qty and price (e.g., "BUY 3 @ $27.00")  
✅ Timestamp tracking for each trade  
✅ Symbol filtering (only shows relevant trades per chart)  
✅ Idempotent (duplicate detection prevents duplicate markers)  
✅ Weekly update cycle (no continuous automation needed)  
✅ Multi-currency support (USD, EUR, etc.)  
✅ Clean state management (old trades can be archived)  

## Next Steps

1. Build Node.js API server with CSV parser
2. Write Pine Script to fetch and annotate
3. Deploy script to TradingView
4. Test with sample trades
5. Create user guide for weekly updates
