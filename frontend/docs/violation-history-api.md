# Violation History API Documentation

## Overview

The Violation History API provides comprehensive tracking and reporting of MAP (Minimum Advertised Price) violations over time. It records every violation event, tracks price changes, and provides detailed analytics and reporting capabilities.

## Key Features

- **Historical Tracking**: Records every violation with timestamps, prices, and changes
- **Price Change Detection**: Tracks when competitor prices change during violations
- **Aggregated Statistics**: Provides summary statistics and time-series data
- **Export Capabilities**: Export violation history as CSV for reporting
- **Filtering & Grouping**: Filter by brand, competitor, date range, and group by time periods

## API Endpoints

### 1. Scan and Record Violations

**POST** `/api/price-monitor/violation-history/scan-and-record`

Scans for MAP violations and records them in the violation history table.

**Request Body:**
```json
{
  "brands": ["Profitec", "Eureka"],
  "severity_filter": "moderate",
  "record_history": true,
  "capture_screenshots": false,
  "dry_run": false
}
```

**Response:**
```json
{
  "message": "MAP violation scan completed",
  "total_matches_scanned": 150,
  "violations_found": 12,
  "history_recorded": 8,
  "by_severity": {
    "minor": 3,
    "moderate": 6,
    "severe": 3
  },
  "violations": [
    {
      "match_id": "abc123",
      "is_new": true,
      "price_changed": false,
      "idc_product": {
        "title": "Profitec Pro 800",
        "vendor": "Profitec",
        "sku": "PRO800",
        "price": 3399.00
      },
      "competitor_product": {
        "title": "Profitec Pro 800 Espresso Machine",
        "vendor": "Profitec",
        "price": 2999.00,
        "competitor": "The Kitchen Barista",
        "domain": "thekitchenbarista.com.au",
        "url": "https://thekitchenbarista.com.au/products/profitec-pro-800"
      },
      "violation": {
        "severity": "moderate",
        "amount": 400.00,
        "percentage": "11.77",
        "first_detected": "2025-01-15T10:30:00Z",
        "last_detected": "2025-08-02T15:45:00Z"
      }
    }
  ]
}
```

### 2. Get Violation History

**GET** `/api/price-monitor/violation-history/history/{productMatchId}`

Retrieves the violation history for a specific product match.

**Query Parameters:**
- `limit` (default: 100): Number of records to return
- `offset` (default: 0): Number of records to skip
- `start_date`: Filter violations after this date (ISO format)
- `end_date`: Filter violations before this date (ISO format)

**Response:**
```json
{
  "history": [
    {
      "id": "violation123",
      "product_match_id": "match456",
      "violation_type": "map_violation_moderate",
      "competitor_price": 2999.00,
      "idc_price": 3399.00,
      "violation_amount": 400.00,
      "violation_percent": 11.77,
      "previous_price": 3099.00,
      "price_change": -100.00,
      "screenshot_url": null,
      "competitor_url": "https://competitor.com/product",
      "notes": "Price changed",
      "detected_at": "2025-08-02T15:45:00Z",
      "product_matches": {
        "idc_products": { ... },
        "competitor_products": { ... }
      }
    }
  ],
  "pagination": {
    "total": 25,
    "limit": 100,
    "offset": 0,
    "has_more": false
  }
}
```

### 3. Get Violation Statistics

**GET** `/api/price-monitor/violation-history/statistics`

Retrieves aggregated violation statistics with time-series data.

**Query Parameters:**
- `brand`: Filter by brand name
- `competitor`: Filter by competitor name
- `start_date`: Start date for analysis
- `end_date`: End date for analysis
- `group_by`: Time grouping (`day`, `week`, `month`)

**Response:**
```json
{
  "summary": {
    "total_violations": 156,
    "active_violations": 42,
    "average_violation_percent": 8.5,
    "average_violation_amount": 245.50,
    "max_violation_percent": 22.3,
    "max_violation_amount": 800.00
  },
  "by_type": [
    {
      "violation_type": "map_violation_severe",
      "_count": { "id": 12 },
      "_sum": { "violation_amount": 4800.00 },
      "_avg": { "violation_percent": 18.5 }
    }
  ],
  "time_series": [
    {
      "period": "2025-08-01",
      "violation_count": 8,
      "avg_violation_pct": 9.2,
      "total_impact": 1840.00,
      "unique_products": 6
    }
  ],
  "filters": {
    "brand": "Profitec",
    "competitor": null,
    "start_date": "2025-07-01",
    "end_date": "2025-08-02",
    "group_by": "day"
  }
}
```

### 4. Export Violation History

**GET** `/api/price-monitor/violation-history/export`

Exports violation history data in CSV or JSON format.

**Query Parameters:**
- `brand`: Filter by brand
- `competitor`: Filter by competitor
- `start_date`: Start date for export
- `end_date`: End date for export
- `format`: Export format (`csv` or `json`)

**CSV Response Headers:**
```
Content-Type: text/csv
Content-Disposition: attachment; filename="violation-history-2025-08-02.csv"
```

**CSV Format:**
```csv
Date,Brand,Product,SKU,MAP Price,Competitor,Competitor Price,Violation Amount,Violation %,Type,Notes
2025-08-02T15:45:00Z,Profitec,"Profitec Pro 800",PRO800,3399.00,The Kitchen Barista,2999.00,400.00,11.77,map_violation_moderate,"Price changed"
```

## Violation Severity Levels

- **Minor**: 1-10% below MAP
- **Moderate**: 10-20% below MAP
- **Severe**: 20%+ below MAP

## Data Model

### violation_history Table

| Field | Type | Description |
|-------|------|-------------|
| id | String | Unique violation record ID |
| product_match_id | String | Foreign key to product_matches |
| violation_type | String | Type of violation (e.g., map_violation_severe) |
| competitor_price | Decimal | Competitor's price at time of violation |
| idc_price | Decimal | IDC's MAP price |
| violation_amount | Decimal | Dollar amount below MAP |
| violation_percent | Float | Percentage below MAP |
| previous_price | Decimal | Previous competitor price (if changed) |
| price_change | Decimal | Price change amount |
| screenshot_url | String | URL to price screenshot |
| competitor_url | String | URL to competitor's product page |
| notes | String | Additional notes |
| detected_at | DateTime | When violation was detected |
| updated_at | DateTime | Last update timestamp |

## Usage Examples

### Daily Violation Monitoring
```bash
# Scan for violations daily
curl -X POST http://localhost:5173/api/price-monitor/violation-history/scan-and-record \
  -H "Content-Type: application/json" \
  -d '{"brands": ["Profitec", "Eureka"], "record_history": true}'
```

### Generate Monthly Report
```bash
# Export last month's violations
curl "http://localhost:5173/api/price-monitor/violation-history/export?format=csv&start_date=2025-07-01&end_date=2025-07-31" \
  -o violations-july-2025.csv
```

### Track Specific Product
```bash
# Get violation history for a product match
curl "http://localhost:5173/api/price-monitor/violation-history/history/match123?limit=50"
```

## Integration with Existing Systems

The violation history system integrates with:

1. **Product Matches**: Links to existing product match records
2. **Price Alerts**: Can trigger alerts for new violations
3. **MAP Violations**: Updates the is_map_violation flag on product matches
4. **Reporting**: Provides data for compliance reporting

## Best Practices

1. **Regular Scanning**: Run violation scans at least daily
2. **Historical Data**: Keep at least 12 months of violation history
3. **Screenshot Evidence**: Consider enabling screenshot capture for severe violations
4. **Reporting**: Generate monthly reports for brand compliance teams
5. **Alert Thresholds**: Set up alerts for severe violations requiring immediate action

## Performance Considerations

- Violation scans are optimized to only record new violations or price changes
- Time-series queries use database aggregations for efficiency
- Large exports should be paginated or filtered by date range
- Consider archiving old violation data after 12-18 months