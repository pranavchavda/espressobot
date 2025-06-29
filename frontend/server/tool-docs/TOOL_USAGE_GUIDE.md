# Python Tools Usage Guide

## Overview
Python tools are located in `/home/pranav/espressobot/frontend/python-tools/`. Each tool is a standalone Python script that can be executed via bash commands.

## Common Tool Patterns

### Product Search
```bash
python3 /home/pranav/espressobot/frontend/python-tools/search_products.py "query" [options]
# Options: --status active/draft/archived, --limit N, --vendor "name"
```

### Product Operations
```bash
# Get product details
python3 /home/pranav/espressobot/frontend/python-tools/get_product.py "SKU123"

# Update pricing
python3 /home/pranav/espressobot/frontend/python-tools/update_pricing.py "SKU123" --price 49.99

# Manage tags
python3 /home/pranav/espressobot/frontend/python-tools/manage_tags.py add "SKU123" "tag1,tag2"
python3 /home/pranav/espressobot/frontend/python-tools/manage_tags.py remove "SKU123" "tag1"
```

### Bulk Operations
```bash
# Bulk price update via CSV
echo "SKU123,49.99" > /tmp/prices.csv
echo "SKU456,99.99" >> /tmp/prices.csv
python3 /home/pranav/espressobot/frontend/python-tools/bulk_price_update.py /tmp/prices.csv
```

### GraphQL Operations
```bash
# Run GraphQL query
python3 /home/pranav/espressobot/frontend/python-tools/graphql_query.py "{ products(first: 5) { edges { node { id title } } } }"

# Run GraphQL mutation
python3 /home/pranav/espressobot/frontend/python-tools/graphql_mutation.py "mutation { productUpdate(...) { product { id } } }"
```

## Tool Composition Examples

### Find and Update Pattern
```bash
# Find products, then update them
python3 search_products.py "coffee" --status active | \
  jq -r '.[] | .sku' | \
  while read sku; do
    python3 update_pricing.py "$sku" --price 39.99
  done
```

### Export and Process Pattern
```bash
# Export product data and process
python3 search_products.py "grinder" > /tmp/grinders.json
cat /tmp/grinders.json | jq '.[] | select(.price > 100)' > /tmp/expensive_grinders.json
```

### Parallel Processing Pattern
```bash
# Update multiple products in parallel
for sku in SKU1 SKU2 SKU3; do
  python3 update_status.py "$sku" --status active &
done
wait
```

## Error Handling

Most tools return:
- Exit code 0 on success
- Exit code 1 on error
- JSON output to stdout
- Error messages to stderr

Example error checking:
```bash
if python3 get_product.py "SKU123" > /tmp/product.json 2>/tmp/error.log; then
  echo "Product found"
  cat /tmp/product.json
else
  echo "Error occurred:"
  cat /tmp/error.log
fi
```

## Best Practices

1. **Always use absolute paths** for tools
2. **Check tool existence** before use: `ls -la /path/to/tool.py`
3. **Use --help** to understand parameters: `python3 tool.py --help`
4. **Capture output** for processing: `tool.py > output.json`
5. **Check exit codes** for error handling
6. **Use JSON output** for easy parsing with jq
7. **Create temporary files** in /tmp/ for intermediate data

## Common Tool Categories

### Product Management
- search_products.py
- get_product.py
- create_product.py
- create_full_product.py
- update_pricing.py
- update_status.py
- manage_tags.py

### Inventory & Warehouse
- manage_inventory_policy.py
- upload_to_skuvault.py
- manage_skuvault_kits.py

### Special Operations
- create_combo.py (bundle products)
- create_open_box.py (open box items)
- manage_map_sales.py (MAP protected items)
- manage_miele_sales.py (vendor promotions)

### Utilities
- pplx.py (Perplexity AI research)
- manage_redirects.py (URL redirects)
- test_connection.py (verify API access)

## Getting Help

To see available options for any tool:
```bash
python3 /path/to/tool.py --help
```

To list all available tools:
```bash
ls -la /home/pranav/espressobot/frontend/python-tools/*.py
```