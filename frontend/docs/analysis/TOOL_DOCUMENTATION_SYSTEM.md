# Tool Documentation System

This document describes the comprehensive tool documentation system implemented for EspressoBot, providing detailed information about all available tools and how to use them.

## Overview

The tool documentation system consists of:

1. **Automated Tool Discovery**: Scans all available tools in the codebase
2. **Structured Documentation**: Detailed usage information stored in the memory system
3. **Search Interface**: Web UI and CLI tools for accessing documentation
4. **Interactive Examples**: Copy-paste ready examples for each tool

## Available Tools

### Total: 22 documented tools

- **Python Tools**: 16 tools for Shopify operations, memory, research, etc.
- **Orchestrator Tools**: 2 tools for bash execution and task tracking
- **Bash Tools**: 1 tool for file operations
- **Guides**: 3 comprehensive usage guides

## Accessing Tool Documentation

### 1. Web Interface

Visit `/tools` in the web application to access the interactive tool documentation browser:

- **Search and Filter**: Find tools by name, tags, or description
- **Category Filtering**: Filter by tool type (Python, Orchestrator, Bash, Guides)
- **Full Documentation**: Click any tool to see complete usage examples
- **Priority Indicators**: Visual priority levels (High/Medium/Low)

### 2. Command Line Interface

Use the search script for quick access from the command line:

```bash
# Show all tools
node scripts/search-tool-docs.js

# Search for specific tools
node scripts/search-tool-docs.js shopify
node scripts/search-tool-docs.js python

# Show full documentation for a tool
node scripts/search-tool-docs.js search_products --show-full

# List available categories
node scripts/search-tool-docs.js --list-categories
```

### 3. API Access

Access tool documentation programmatically via the REST API:

```bash
# Get all tool documentation
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:5173/api/prompt-library?category=tools"

# Search tool documentation
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:5173/api/prompt-library/search?query=shopify"
```

## Tool Categories

### Python Tools (`python-tools/` directory)

High-priority core tools:
- `search_products` - Advanced product search with Shopify query syntax
- `get_product` - Retrieve product details by ID/handle/SKU
- `create_product` - Create simple products
- `create_full_product` - Create products with multiple variants
- `update_pricing` - Update product prices
- `bulk_price_update` - Bulk price operations
- `memory_operations` - Search and retrieve user memories
- `graphql_query` - Custom GraphQL queries
- `graphql_mutation` - Custom GraphQL mutations

Medium-priority specialized tools:
- `manage_tags` - Add/remove product tags
- `update_status` - Change product status
- `create_combo` - Create bundle products
- `create_open_box` - Create open box variants
- `manage_inventory_policy` - Control overselling behavior
- `update_conversation_topic` - Update conversation titles
- `pplx` - Perplexity AI research

### Orchestrator Tools

- `bash` - Execute bash commands with safety checks
- `task_tracking` - Track and report task progress

### Bash Tools

- `file_operations` - Read, write, and manipulate files

### Guides

- `usage_patterns` - Best practices for tool usage
- `tool_combinations` - Common tool workflow patterns
- `tools_summary` - Complete overview of all available tools

## Documentation Structure

Each tool document includes:

```markdown
# Tool: tool_name
**Purpose**: Brief description of what the tool does
**Python Path**: path/to/tool.py (for Python tools)
**Access**: How to access the tool (for orchestrator tools)

**Parameters**:
- param1 (required): Description
- param2 (optional): Description with default value

**Example Usage**:
```bash
# Example command with explanation
python python-tools/tool_name.py --param1 value --param2 value

# More complex example
python python-tools/tool_name.py \
  --param1 "complex value" \
  --param2 value \
  --flag
```

**Output**: Description of expected output
```

## Adding New Tool Documentation

### 1. For Python Tools

Create a new entry in the documentation script:

```javascript
{
  fragment: `# Tool: your_tool_name
**Purpose**: What your tool does
**Python Path**: python-tools/your_tool.py

**Parameters**:
- param1 (required): Description
- param2 (optional): Description

**Example Usage**:
\`\`\`bash
python python-tools/your_tool.py --param1 value
\`\`\`

**Output**: Expected output description`,
  metadata: {
    category: 'tools',
    agent_type: 'all',
    priority: 'high', // or 'medium', 'low'
    tags: ['relevant', 'tags', 'here'],
    tool_name: 'your_tool_name',
    tool_type: 'python'
  }
}
```

### 2. For JavaScript/Orchestrator Tools

```javascript
{
  fragment: `# Tool: your_tool_name
**Purpose**: What your tool does
**Access**: How to access through orchestrator

**Example Usage**:
\`\`\`javascript
const result = await tools.your_tool_name({
  param1: 'value',
  param2: 'value'
});
\`\`\``,
  metadata: {
    category: 'tools',
    agent_type: 'all',
    priority: 'medium',
    tags: ['relevant', 'tags'],
    tool_name: 'your_tool_name',
    tool_type: 'orchestrator'
  }
}
```

### 3. Update Documentation

Run the documentation script to add your new tool:

```bash
node scripts/add-tool-documentation.js
```

## Common Usage Patterns

### 1. Product Management Workflow

```bash
# 1. Search for existing products
python python-tools/search_products.py "vendor:DeLonghi"

# 2. Get detailed product info
python python-tools/get_product.py --handle "product-handle" --fields all

# 3. Update pricing
python python-tools/update_pricing.py --product-id "gid://shopify/Product/123" --price 299.99

# 4. Update tags
python python-tools/manage_tags.py --product-id "gid://shopify/Product/123" --add "sale,featured"

# 5. Activate product
python python-tools/update_status.py --product-id "gid://shopify/Product/123" --status ACTIVE
```

### 2. Memory-Augmented Research

```bash
# 1. Search existing memories
python python-tools/memory_operations.py search "DeLonghi Dedica"

# 2. Research with Perplexity
python python-tools/pplx.py "DeLonghi EC685M specifications and features"

# 3. Create product based on research
python python-tools/create_product.py \
  --title "DeLonghi Dedica Style EC685M" \
  --vendor "DeLonghi" \
  --type "Espresso Machines" \
  --price 249.99

# 4. Update conversation topic
python python-tools/update_conversation_topic.py 0 "DeLonghi Product Research and Creation"
```

### 3. Bulk Operations

```bash
# 1. Search for products to update
python python-tools/search_products.py "tag:sale" --fields id,title,price > sale_products.json

# 2. Prepare bulk price updates (CSV format)
echo "product_id,price,compare_at_price" > price_updates.csv
echo "gid://shopify/Product/123,199.99,299.99" >> price_updates.csv

# 3. Execute bulk update
python python-tools/bulk_price_update.py price_updates.csv
```

## Best Practices

1. **Always check tool documentation** before using unfamiliar tools
2. **Use the search interface** to quickly find relevant tools
3. **Follow the examples** provided in each tool's documentation
4. **Chain tools together** for complex workflows
5. **Update conversation topics** when starting new tasks
6. **Store important results** in memory for future reference

## Troubleshooting

### Common Issues

1. **Tool not found**: Check tool name spelling and run `node scripts/search-tool-docs.js` to see available tools

2. **Permission errors**: Ensure you're authenticated and have proper permissions

3. **Python tool errors**: Check that all required parameters are provided and properly formatted

4. **GraphQL errors**: Validate your GraphQL syntax and check Shopify API documentation

### Getting Help

1. Use the web interface at `/tools` for interactive documentation
2. Run `node scripts/search-tool-docs.js --help` for CLI help
3. Search memories for previous solutions: `python python-tools/memory_operations.py search "your issue"`
4. Check the tool's source code in `python-tools/` for advanced usage

## Implementation Details

### File Locations

- **Documentation Data**: `server/memory/data/espressobot_memory.db`
- **Python Tools**: `python-tools/*.py`
- **JavaScript Tools**: `server/tools/*.js`
- **Web Interface**: `src/components/ToolDocumentation.jsx`
- **CLI Interface**: `scripts/search-tool-docs.js`
- **Documentation Generator**: `scripts/add-tool-documentation.js`

### Technology Stack

- **Storage**: SQLite database with semantic search
- **Backend**: Express.js API with authentication
- **Frontend**: React with Tailwind CSS
- **CLI**: Node.js with argument parsing
- **Memory System**: Local embeddings with OpenAI integration

### Performance

- **Search Speed**: ~100ms for memory searches
- **Documentation Load**: ~200ms for full tool list
- **Web Interface**: Responsive with real-time filtering
- **CLI Interface**: Instant results for cached queries

---

*Last Updated: July 2, 2025*
*Total Tools Documented: 22*
*Documentation Entries: 75+*