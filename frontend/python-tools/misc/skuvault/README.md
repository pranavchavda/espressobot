# SkuVault Product Fetcher

This tool retrieves product information from SkuVault's API, including product codes, descriptions, quantities, and pricing.

## Purpose

The `get_skuvault_products.py` script is used to:
- Fetch SkuVault product codes for given SKUs
- Retrieve current inventory quantities (on hand and available)
- Get product descriptions and pricing information
- Export data in CSV or JSON format for further processing

## Prerequisites

Set the following environment variables:
```bash
export SKUVAULT_TENANT_TOKEN="your_tenant_token"
export SKUVAULT_USER_TOKEN="your_user_token"
```

## Usage

### Fetch specific SKUs
```bash
python get_skuvault_products.py --skus ECM-G1041-B ECM-P6025 BEZ-7819901
```

### Fetch SKUs from CSV file
```bash
python get_skuvault_products.py --csv quantityBuffer.csv --sku-column SKU
```

### Save results to files
```bash
# Save as JSON
python get_skuvault_products.py --csv input.csv --output-json results.json

# Save as CSV
python get_skuvault_products.py --csv input.csv --output-csv results.csv

# Save both formats
python get_skuvault_products.py --csv input.csv --output-json results.json --output-csv results.csv
```

### Verbose output
```bash
python get_skuvault_products.py --skus ECM-G1041-B --verbose
```

## Command Line Options

- `--skus`: List of SKUs to fetch (space-separated)
- `--csv`: Path to CSV file containing SKUs
- `--sku-column`: Column name for SKUs in CSV (default: "SKU")
- `--output-json`: Path for JSON output file
- `--output-csv`: Path for CSV output file
- `--verbose`: Show detailed product information

## Output Format

### JSON Output
```json
[
  {
    "SKU": "ECM-G1041-B",
    "Code": "4156750315",
    "Description": "ECM/Profitec 64mm Burr Set",
    "QuantityAvailable": 14,
    "QuantityOnHand": 14,
    "Cost": 0.0,
    "SalePrice": 69.8,
    "Channels": []
  }
]
```

### CSV Output
```csv
SKU,Code,Description,Quantity Available,Quantity On Hand,Cost,Sale Price
ECM-G1041-B,4156750315,ECM/Profitec 64mm Burr Set,14,14,0.0,69.8
```

## Common Use Cases

### 1. Update Buffer Quantities
Fetch current inventory levels and codes for products that need buffer quantity adjustments:
```bash
python get_skuvault_products.py --csv quantityBuffer.csv --output-csv updated_buffer.csv
```

### 2. Inventory Audit
Get current stock levels for specific SKUs:
```bash
python get_skuvault_products.py --skus ECM-G1041-B ECM-P6025 --verbose
```

### 3. Bulk Code Retrieval
Get SkuVault codes for a list of SKUs to update other systems:
```bash
python get_skuvault_products.py --csv sku_list.csv --output-json codes.json
```

## Notes

- The tool uses the `/api/products/getProducts` endpoint
- Authentication tokens are included in the request body (not headers)
- Channel-specific quantities are extracted if available in the response
- The tool handles both primary and alternate SKUs

## Buffer Quantity Tools (Experimental)

### explore_buffer_api.py
An exploratory tool to find the correct API endpoint for setting buffer quantities:

```bash
# Test all potential endpoints
python explore_buffer_api.py --sku "ECM-G1041-B"

# Test only product-related endpoints
python explore_buffer_api.py --sku "ECM-G1041-B" --test product

# Test channel-specific endpoints
python explore_buffer_api.py --sku "ECM-G1041-B" --channel "Shopify" --test channel
```

This tool tests various potential endpoints and field names to discover how to set buffer quantities via the API.

### set_channel_quantity.py
Experimental tool for setting channel-specific quantities (may not work without proper endpoint):

```bash
# List available channels
python set_channel_quantity.py list-channels

# Set quantity for a specific channel
python set_channel_quantity.py set --sku "ECM-G1041-B" --channel "Shopify" --quantity 10

# Bulk set from CSV
python set_channel_quantity.py bulk-set --csv channel_quantities.csv
```

### set_buffer_quantity.py
Set buffer quantities for products in SkuVault to reserve inventory for repairs or other purposes:

```bash
# Set buffer for a single SKU
python set_buffer_quantity.py --sku "ECM-G1041-B" --buffer 3 --mode cutoff

# Set buffers from CSV file
python set_buffer_quantity.py --csv quantityBuffer.csv

# Preview changes without applying
python set_buffer_quantity.py --csv quantityBuffer.csv --dry-run
```

#### Buffer Modes:
- **cutoff**: Stop selling when inventory reaches buffer quantity (reserves items for repairs)
- **reserve**: Always show buffer quantity as available (not commonly used)

#### CSV Format:
The tool accepts CSV files with the following columns:
- `SKU` (required): Product SKU
- `Buffer quantity` or `Buffer Quantity` (required): Number to reserve
- `Buffer Quantity Mode` (optional): "cutoff" or "reserve" (defaults to cutoff)

Example CSV:
```csv
Code,SKU,Buffer Quantity Mode,Buffer quantity
4156750315,ECM-G1041-B,cutoff,3
4156747111,ECM-P6025,cutoff,15
```

#### Rate Limiting:
- SkuVault API allows 10 requests per minute
- The tool automatically waits 60 seconds after every 10 requests
- Failed requests due to rate limiting are automatically retried

#### How It Works:
The tool uses the `updateProduct` endpoint with buffer-related fields. Through testing, we discovered that SkuVault accepts:
- `BufferQuantity`: The quantity to reserve
- `LowQuantityCutoff`: Alternative field name for buffer
- `MinimumQuantity`: Another alternative field name
- `BufferMode`: The buffer mode (cutoff/reserve)

**Note**: The buffer API functionality was discovered through testing. While it works reliably, it's not officially documented in SkuVault's public API docs.