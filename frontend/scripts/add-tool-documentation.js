#!/usr/bin/env node

/**
 * Script to add comprehensive tool documentation to the prompt library
 */

import { memoryOperations } from '../server/memory/memory-operations-local.js';

// Tool documentation entries
const toolDocumentation = [
  // ===== PRODUCT MANAGEMENT TOOLS =====
  {
    fragment: `# Tool: search_products
**Purpose**: Search for products in Shopify using advanced query syntax
**Python Path**: python-tools/search_products.py

**Parameters**:
- query (required): Search query using Shopify syntax
- limit: Number of results (default: 10)
- fields: Which fields to include (id, title, handle, vendor, status, tags, price, inventory, variants, seo, all)

**Query Syntax Examples**:
- Basic: "coffee" or "espresso machine"
- Tags: "tag:sale" or "tag:featured tag:new"
- Type/Vendor: "product_type:Electronics" or "vendor:Apple"
- Price: "price:>50" or "price:10..100"
- Status: "status:active" or "status:draft"
- Inventory: "inventory_quantity:>0"
- SKU/Handle: "sku:ESP-001" or "handle:delonghi-espresso"
- Combinations: "coffee tag:premium price:>100"
- Negative: "coffee -decaf" or "tag:sale -tag:clearance"

**Example Usage**:
\`\`\`bash
python python-tools/search_products.py "tag:sale status:active" --limit 20
python python-tools/search_products.py "vendor:DeLonghi" --fields all
python python-tools/search_products.py "price:>100 inventory_quantity:>0"
\`\`\`

**Output**: JSON array of products with requested fields`,
    metadata: {
      category: 'tools',
      agent_type: 'all',
      priority: 'high',
      tags: ['shopify', 'products', 'search', 'python-tool'],
      tool_name: 'search_products',
      tool_type: 'python'
    }
  },

  {
    fragment: `# Tool: get_product
**Purpose**: Get detailed information about a specific product
**Python Path**: python-tools/get_product.py

**Parameters**:
- One of these is required:
  - id: Product ID (e.g., "gid://shopify/Product/123456")
  - handle: Product handle (e.g., "delonghi-espresso-machine")
  - sku: Product SKU (search through variants)
- fields: Which fields to include (basic, variants, images, seo, metafields, all)

**Example Usage**:
\`\`\`bash
# By ID
python python-tools/get_product.py --id "gid://shopify/Product/123456"

# By handle
python python-tools/get_product.py --handle "delonghi-dedica-style"

# By SKU with all fields
python python-tools/get_product.py --sku "EC685M" --fields all

# Get specific fields
python python-tools/get_product.py --handle "product-handle" --fields basic variants images
\`\`\`

**Output**: JSON object with product details`,
    metadata: {
      category: 'tools',
      agent_type: 'all',
      priority: 'high',
      tags: ['shopify', 'products', 'get', 'python-tool'],
      tool_name: 'get_product',
      tool_type: 'python'
    }
  },

  {
    fragment: `# Tool: create_product
**Purpose**: Create a new product in Shopify
**Python Path**: python-tools/create_product.py

**Parameters**:
- title (required): Product title
- vendor (required): Product vendor/brand
- type (required): Product type/category
- description: Product description (HTML supported)
- tags: Comma-separated list of tags
- price: Product price (default: 0.00)
- sku: Product SKU
- barcode: Product barcode
- weight: Product weight
- weight_unit: Weight unit (GRAMS, KILOGRAMS, OUNCES, POUNDS)
- inventory: Initial inventory quantity
- no_track_inventory: Disable inventory tracking
- status: Product status (DRAFT, ACTIVE, ARCHIVED)

**Example Usage**:
\`\`\`bash
# Simple product
python python-tools/create_product.py --title "Test Product" --vendor "Brand" --type "Category"

# Full product details
python python-tools/create_product.py \\
  --title "DeLonghi Dedica Style EC685M" \\
  --vendor "DeLonghi" \\
  --type "Espresso Machines" \\
  --description "Compact espresso machine with professional features" \\
  --tags "espresso-machines,delonghi,consumer" \\
  --price 249.99 \\
  --sku "EC685M" \\
  --inventory 10 \\
  --status ACTIVE

# Digital product without inventory
python python-tools/create_product.py --title "Digital Gift Card" --vendor "Store" --type "Gift Cards" --no-track-inventory
\`\`\`

**Output**: Success message with product ID, handle, and variant details`,
    metadata: {
      category: 'tools',
      agent_type: 'all',
      priority: 'high',
      tags: ['shopify', 'products', 'create', 'python-tool'],
      tool_name: 'create_product',
      tool_type: 'python'
    }
  },

  {
    fragment: `# Tool: create_full_product
**Purpose**: Create a product with multiple variants and full details
**Python Path**: python-tools/create_full_product.py

**Parameters**:
- title (required): Product title
- vendor (required): Product vendor
- product_type (required): Product type
- description: Product description
- tags: List of tags
- variants: List of variant objects with:
  - title: Variant title (e.g., "Small", "Red")
  - price: Variant price
  - sku: Variant SKU
  - barcode: Variant barcode
  - inventory_quantity: Stock quantity
  - weight: Variant weight
  - options: List of option values
- options: Product options (e.g., ["Size", "Color"])
- images: List of image URLs

**Example Usage**:
\`\`\`bash
# Product with size variants
python python-tools/create_full_product.py \\
  --title "Premium T-Shirt" \\
  --vendor "Fashion Brand" \\
  --product-type "Apparel" \\
  --options "Size" "Color" \\
  --variant-json '[
    {"title": "Small / Black", "price": "29.99", "sku": "TS-S-BLK", "inventory_quantity": 50},
    {"title": "Medium / Black", "price": "29.99", "sku": "TS-M-BLK", "inventory_quantity": 100},
    {"title": "Large / Black", "price": "29.99", "sku": "TS-L-BLK", "inventory_quantity": 75}
  ]'
\`\`\``,
    metadata: {
      category: 'tools',
      agent_type: 'all',
      priority: 'high',
      tags: ['shopify', 'products', 'create', 'variants', 'python-tool'],
      tool_name: 'create_full_product',
      tool_type: 'python'
    }
  },

  {
    fragment: `# Tool: update_pricing
**Purpose**: Update product or variant pricing
**Python Path**: python-tools/update_pricing.py

**Parameters**:
- One identifier required:
  - product_id: Update all variants of a product
  - variant_id: Update specific variant
  - sku: Update variant by SKU
- price: New price (required)
- compare_at_price: Original/compare price (optional)

**Example Usage**:
\`\`\`bash
# Update product price (all variants)
python python-tools/update_pricing.py --product-id "gid://shopify/Product/123456" --price 199.99

# Update specific variant
python python-tools/update_pricing.py --variant-id "gid://shopify/ProductVariant/789" --price 149.99 --compare-at 199.99

# Update by SKU
python python-tools/update_pricing.py --sku "EC685M" --price 249.99
\`\`\`

**Output**: Success message with updated price details`,
    metadata: {
      category: 'tools',
      agent_type: 'all',
      priority: 'high',
      tags: ['shopify', 'products', 'pricing', 'update', 'python-tool'],
      tool_name: 'update_pricing',
      tool_type: 'python'
    }
  },

  {
    fragment: `# Tool: bulk_price_update
**Purpose**: Update prices for multiple products/variants in one operation
**Python Path**: python-tools/bulk_price_update.py

**Parameters**:
- CSV file with columns: product_id/variant_id/sku, price, compare_at_price
- Or inline updates via JSON

**Example Usage**:
\`\`\`bash
# From CSV file
python python-tools/bulk_price_update.py prices.csv

# Inline updates
python python-tools/bulk_price_update.py --updates '[
  {"sku": "ABC123", "price": "99.99", "compare_at_price": "149.99"},
  {"product_id": "gid://shopify/Product/123", "price": "199.99"},
  {"variant_id": "gid://shopify/ProductVariant/456", "price": "79.99"}
]'
\`\`\`

**CSV Format**:
\`\`\`csv
sku,price,compare_at_price
ABC123,99.99,149.99
DEF456,79.99,
\`\`\``,
    metadata: {
      category: 'tools',
      agent_type: 'all',
      priority: 'high',
      tags: ['shopify', 'products', 'pricing', 'bulk', 'python-tool'],
      tool_name: 'bulk_price_update',
      tool_type: 'python'
    }
  },

  {
    fragment: `# Tool: manage_tags
**Purpose**: Add or remove tags from products
**Python Path**: python-tools/manage_tags.py

**Parameters**:
- product_id (required): Product to update
- add_tags: Tags to add (comma-separated or list)
- remove_tags: Tags to remove (comma-separated or list)

**Example Usage**:
\`\`\`bash
# Add tags
python python-tools/manage_tags.py --product-id "gid://shopify/Product/123" --add "sale,featured,summer-2024"

# Remove tags
python python-tools/manage_tags.py --product-id "gid://shopify/Product/123" --remove "old-season,clearance"

# Add and remove in one operation
python python-tools/manage_tags.py --product-id "gid://shopify/Product/123" --add "new-arrival" --remove "coming-soon"
\`\`\`

**Output**: Updated tag list`,
    metadata: {
      category: 'tools',
      agent_type: 'all',
      priority: 'medium',
      tags: ['shopify', 'products', 'tags', 'python-tool'],
      tool_name: 'manage_tags',
      tool_type: 'python'
    }
  },

  {
    fragment: `# Tool: update_status
**Purpose**: Update product status (ACTIVE, DRAFT, ARCHIVED)
**Python Path**: python-tools/update_status.py

**Parameters**:
- product_id (required): Product to update
- status (required): New status (ACTIVE, DRAFT, ARCHIVED)

**Example Usage**:
\`\`\`bash
# Activate a product
python python-tools/update_status.py --product-id "gid://shopify/Product/123" --status ACTIVE

# Archive a product
python python-tools/update_status.py --product-id "gid://shopify/Product/123" --status ARCHIVED

# Set to draft
python python-tools/update_status.py --product-id "gid://shopify/Product/123" --status DRAFT
\`\`\``,
    metadata: {
      category: 'tools',
      agent_type: 'all',
      priority: 'medium',
      tags: ['shopify', 'products', 'status', 'python-tool'],
      tool_name: 'update_status',
      tool_type: 'python'
    }
  },

  // ===== MEMORY OPERATIONS =====
  {
    fragment: `# Tool: memory_operations
**Purpose**: Search and retrieve memories for the current user
**Python Path**: python-tools/memory_operations.py

**Operations**:
1. **search**: Search memories by keyword
   - Parameters: query (required), limit (default: 10)
   
2. **get_all**: Get all memories for the user
   - Parameters: limit (default: 100)

3. **add**: Add new memory (requires JS backend for embeddings)
   - Currently shows error directing to use memory tool through orchestrator

**Example Usage**:
\`\`\`bash
# Search memories
python python-tools/memory_operations.py search "shopify API" --limit 20
python python-tools/memory_operations.py search "product creation"

# Get all memories
python python-tools/memory_operations.py get_all
python python-tools/memory_operations.py get_all --limit 50
\`\`\`

**Output**: JSON with memories array containing id, memory content, metadata, and created_at

**Note**: The tool automatically uses the current user context from environment variables`,
    metadata: {
      category: 'tools',
      agent_type: 'all',
      priority: 'high',
      tags: ['memory', 'search', 'python-tool'],
      tool_name: 'memory_operations',
      tool_type: 'python'
    }
  },

  // ===== CONVERSATION TOOLS =====
  {
    fragment: `# Tool: update_conversation_topic
**Purpose**: Update the topic/title of a conversation for better organization
**Python Path**: python-tools/update_conversation_topic.py

**Parameters**:
- conversation_id (required): ID of the conversation (use 0 for current)
- topic_title (required): Concise topic title (max 200 chars)
- details (optional): Detailed description of the topic

**Example Usage**:
\`\`\`bash
# Update current conversation topic
python python-tools/update_conversation_topic.py 0 "Shopify Product Import - DeLonghi Espresso Machines"

# Update with details
python python-tools/update_conversation_topic.py 0 "API Integration Setup" --details "Setting up GraphQL mutations for bulk product updates"

# Update specific conversation
python python-tools/update_conversation_topic.py 42 "Customer Support Automation"
\`\`\`

**Best Practices**:
- Keep titles concise but descriptive
- Include key entities (product names, features, etc.)
- Update when conversation focus changes significantly`,
    metadata: {
      category: 'tools',
      agent_type: 'all',
      priority: 'medium',
      tags: ['conversation', 'organization', 'python-tool'],
      tool_name: 'update_conversation_topic',
      tool_type: 'python'
    }
  },

  // ===== GRAPHQL TOOLS =====
  {
    fragment: `# Tool: graphql_query
**Purpose**: Execute custom GraphQL queries against Shopify Admin API
**Python Path**: python-tools/graphql_query.py

**Parameters**:
- query (required): GraphQL query string
- variables: Query variables as JSON

**Example Usage**:
\`\`\`bash
# Simple query
python python-tools/graphql_query.py "
{
  shop {
    name
    primaryDomain {
      url
    }
  }
}"

# Query with variables
python python-tools/graphql_query.py "
query getProduct($id: ID!) {
  product(id: $id) {
    title
    variants(first: 10) {
      edges {
        node {
          id
          title
          price
        }
      }
    }
  }
}" --variables '{"id": "gid://shopify/Product/123456"}'
\`\`\`

**Output**: Full GraphQL response as JSON`,
    metadata: {
      category: 'tools',
      agent_type: 'all',
      priority: 'high',
      tags: ['shopify', 'graphql', 'query', 'python-tool'],
      tool_name: 'graphql_query',
      tool_type: 'python'
    }
  },

  {
    fragment: `# Tool: graphql_mutation
**Purpose**: Execute custom GraphQL mutations against Shopify Admin API
**Python Path**: python-tools/graphql_mutation.py

**Parameters**:
- mutation (required): GraphQL mutation string
- variables: Mutation variables as JSON

**Example Usage**:
\`\`\`bash
# Update product
python python-tools/graphql_mutation.py "
mutation updateProduct($input: ProductInput!) {
  productUpdate(input: $input) {
    product {
      id
      title
    }
    userErrors {
      field
      message
    }
  }
}" --variables '{
  "input": {
    "id": "gid://shopify/Product/123456",
    "title": "Updated Product Title"
  }
}'
\`\`\`

**Output**: Mutation result with any userErrors`,
    metadata: {
      category: 'tools',
      agent_type: 'all',
      priority: 'high',
      tags: ['shopify', 'graphql', 'mutation', 'python-tool'],
      tool_name: 'graphql_mutation',
      tool_type: 'python'
    }
  },

  // ===== BASH TOOL =====
  {
    fragment: `# Tool: bash (via orchestrator)
**Purpose**: Execute bash commands with safety checks and timeout
**Access**: Available to all agents through orchestrator

**Features**:
- Dangerous command detection (rm -rf, format, etc.)
- Configurable timeout (default: 30s, max: 5min)
- Working directory preservation
- Environment variable access
- Output capture (stdout/stderr)

**Safety Checks**:
The tool will warn or block:
- Recursive deletions (rm -rf)
- System modifications (/etc, /sys, /boot)
- Disk operations (format, dd)
- Package management (without sudo)

**Example Usage**:
\`\`\`javascript
// In agent code
const result = await tools.bash({
  command: 'ls -la',
  cwd: '/home/user/project',
  timeout: 60000 // 60 seconds
});

// Command chaining
const result = await tools.bash({
  command: 'cd /tmp && echo "test" > file.txt && cat file.txt'
});
\`\`\`

**Best Practices**:
- Always use absolute paths
- Check command success before proceeding
- Use timeout for long-running operations
- Escape special characters properly`,
    metadata: {
      category: 'tools',
      agent_type: 'all',
      priority: 'high',
      tags: ['bash', 'system', 'orchestrator-tool'],
      tool_name: 'bash',
      tool_type: 'orchestrator'
    }
  },

  // ===== FILE OPERATIONS =====
  {
    fragment: `# Tool: File Operations (via bash)
**Purpose**: Read, write, and manipulate files

**Common Operations**:

**Reading Files**:
\`\`\`bash
# Read entire file
cat /path/to/file.txt

# Read with line numbers
cat -n /path/to/file.txt

# Read first/last N lines
head -n 20 /path/to/file.txt
tail -n 50 /path/to/file.txt

# Search in file
grep "pattern" /path/to/file.txt
grep -n "pattern" /path/to/file.txt  # with line numbers
\`\`\`

**Writing Files**:
\`\`\`bash
# Create/overwrite file
echo "content" > /path/to/file.txt

# Append to file
echo "additional content" >> /path/to/file.txt

# Multi-line content
cat > /path/to/file.txt << 'EOF'
Line 1
Line 2
Line 3
EOF
\`\`\`

**File Management**:
\`\`\`bash
# Create directory
mkdir -p /path/to/directory

# Copy files
cp source.txt destination.txt
cp -r source_dir/ destination_dir/

# Move/rename
mv old_name.txt new_name.txt

# Delete (use with caution)
rm file.txt
rm -rf directory/  # Will trigger safety warning
\`\`\``,
    metadata: {
      category: 'tools',
      agent_type: 'all',
      priority: 'high',
      tags: ['files', 'bash', 'operations'],
      tool_name: 'file_operations',
      tool_type: 'bash'
    }
  },

  // ===== SPECIALTY TOOLS =====
  {
    fragment: `# Tool: create_combo
**Purpose**: Create combo/bundle products from multiple existing products
**Python Path**: python-tools/create_combo.py

**Parameters**:
- title (required): Combo product title
- product_ids (required): List of product IDs to bundle
- combo_price (required): Total combo price
- description: Combo description
- create_as_draft: Create in draft status (default: true)

**Example Usage**:
\`\`\`bash
# Create espresso machine combo
python python-tools/create_combo.py \\
  --title "Complete Espresso Setup" \\
  --products "gid://shopify/Product/123" "gid://shopify/Product/456" \\
  --price 599.99 \\
  --description "Everything you need to start making espresso at home"
\`\`\``,
    metadata: {
      category: 'tools',
      agent_type: 'all',
      priority: 'medium',
      tags: ['shopify', 'products', 'combo', 'bundle', 'python-tool'],
      tool_name: 'create_combo',
      tool_type: 'python'
    }
  },

  {
    fragment: `# Tool: create_open_box
**Purpose**: Create open box variants of existing products
**Python Path**: python-tools/create_open_box.py

**Parameters**:
- product_id (required): Original product ID
- discount_percentage: Discount percentage (default: 15)
- condition_notes: Condition description
- inventory_quantity: Available quantity (default: 1)

**Example Usage**:
\`\`\`bash
# Create open box variant
python python-tools/create_open_box.py \\
  --product-id "gid://shopify/Product/123456" \\
  --discount 20 \\
  --condition "Open box - inspected and certified. Full warranty." \\
  --inventory 3
\`\`\``,
    metadata: {
      category: 'tools',
      agent_type: 'all',
      priority: 'medium',
      tags: ['shopify', 'products', 'open-box', 'variants', 'python-tool'],
      tool_name: 'create_open_box',
      tool_type: 'python'
    }
  },

  {
    fragment: `# Tool: pplx (Perplexity AI)
**Purpose**: Query Perplexity AI for research and product information
**Python Path**: python-tools/pplx.py

**Parameters**:
- query (required): Question or search query
- focus: Search focus area (web, academic, writing, wolfram, youtube, reddit)
- include_sources: Include source citations (default: true)

**Example Usage**:
\`\`\`bash
# Product research
python python-tools/pplx.py "DeLonghi EC685M espresso machine specifications and features"

# Competitive analysis
python python-tools/pplx.py "best espresso machines under $300 2024" --focus web

# Technical information
python python-tools/pplx.py "espresso extraction pressure temperature relationship" --focus academic
\`\`\`

**Output**: AI-generated response with source citations`,
    metadata: {
      category: 'tools',
      agent_type: 'all',
      priority: 'medium',
      tags: ['research', 'ai', 'perplexity', 'python-tool'],
      tool_name: 'pplx',
      tool_type: 'python'
    }
  },

  // ===== INVENTORY TOOLS =====
  {
    fragment: `# Tool: manage_inventory_policy
**Purpose**: Update inventory policy for products (continue selling when out of stock)
**Python Path**: python-tools/manage_inventory_policy.py

**Parameters**:
- product_id (required): Product to update
- policy (required): DENY (stop selling) or CONTINUE (allow overselling)
- apply_to_all_variants: Apply to all variants (default: true)

**Example Usage**:
\`\`\`bash
# Allow overselling (pre-orders)
python python-tools/manage_inventory_policy.py \\
  --product-id "gid://shopify/Product/123" \\
  --policy CONTINUE

# Stop selling when out of stock
python python-tools/manage_inventory_policy.py \\
  --product-id "gid://shopify/Product/123" \\
  --policy DENY
\`\`\``,
    metadata: {
      category: 'tools',
      agent_type: 'all',
      priority: 'medium',
      tags: ['shopify', 'inventory', 'policy', 'python-tool'],
      tool_name: 'manage_inventory_policy',
      tool_type: 'python'
    }
  },

  // ===== TASK TRACKING =====
  {
    fragment: `# Tool: Task Tracking (via orchestrator)
**Purpose**: Track and report progress on tasks from task plans

**Available Functions**:
1. **report_task_progress**: Update task status
   - Parameters: taskId, status (in_progress/completed/blocked), message, conversationId
   
2. **mark_task_complete**: Mark task as completed
   - Parameters: taskId, result, conversationId

**Example Usage**:
\`\`\`javascript
// Starting a task
await tools.report_task_progress({
  taskId: 't1',
  status: 'in_progress',
  message: 'Starting product import process',
  conversationId: context.conversationId
});

// Completing a task
await tools.mark_task_complete({
  taskId: 't1',
  result: 'Successfully imported 25 products',
  conversationId: context.conversationId
});

// Blocking a task
await tools.report_task_progress({
  taskId: 't2',
  status: 'blocked',
  message: 'Waiting for API credentials',
  conversationId: context.conversationId
});
\`\`\``,
    metadata: {
      category: 'tools',
      agent_type: 'all',
      priority: 'medium',
      tags: ['tasks', 'tracking', 'orchestrator-tool'],
      tool_name: 'task_tracking',
      tool_type: 'orchestrator'
    }
  },

  // ===== TOOL USAGE PATTERNS =====
  {
    fragment: `# Tool Usage Best Practices

**1. Error Handling**:
Always check for errors in tool responses:
\`\`\`bash
result=$(python python-tools/search_products.py "test" 2>&1)
if [ $? -ne 0 ]; then
  echo "Error: $result"
  exit 1
fi
\`\`\`

**2. Chaining Operations**:
Many tasks require multiple tools:
\`\`\`bash
# Search, modify, update pattern
product_id=$(python python-tools/search_products.py "sku:ABC123" | jq -r '.edges[0].node.id')
python python-tools/update_pricing.py --product-id "$product_id" --price 99.99
python python-tools/manage_tags.py --product-id "$product_id" --add "sale,featured"
\`\`\`

**3. Bulk Operations**:
Use bulk tools when updating multiple items:
- Prefer bulk_price_update over multiple update_pricing calls
- Use GraphQL mutations for complex bulk updates

**4. Memory Integration**:
Store important information for future reference:
\`\`\`bash
# After creating a product
echo "Created product $product_id with SKU $sku" | \\
  python python-tools/memory_operations.py add -
\`\`\`

**5. Conversation Context**:
Update conversation topic when focus changes:
\`\`\`bash
python python-tools/update_conversation_topic.py 0 \\
  "Bulk Import - $(date +%Y-%m-%d)" \\
  --details "Imported 50 products from CSV"
\`\`\``,
    metadata: {
      category: 'tools',
      agent_type: 'all',
      priority: 'high',
      tags: ['best-practices', 'patterns', 'usage'],
      tool_name: 'usage_patterns',
      tool_type: 'guide'
    }
  },

  // ===== COMMON TOOL COMBINATIONS =====
  {
    fragment: `# Common Tool Combinations

**Product Research & Creation Flow**:
1. Use pplx to research product details
2. search_products to check if it already exists
3. create_product or create_full_product to add it
4. manage_tags to categorize
5. update_pricing if needed

**Bulk Update Flow**:
1. search_products with specific query
2. Extract IDs/SKUs using jq or grep
3. bulk_price_update or loop with individual updates
4. update_status to activate products

**Memory-Augmented Workflow**:
1. memory_operations search to check previous work
2. Execute main task
3. memory_operations add to store results
4. update_conversation_topic to summarize

**Open Box Creation Flow**:
1. get_product to fetch original details
2. create_open_box with discount
3. manage_tags to add "open-box" tag
4. update_status to ACTIVE if ready

**GraphQL for Complex Operations**:
Use graphql_query/mutation when:
- Need fields not available in standard tools
- Performing complex bulk operations
- Accessing newer API features
- Need precise control over the operation`,
    metadata: {
      category: 'tools',
      agent_type: 'all',
      priority: 'medium',
      tags: ['workflows', 'combinations', 'patterns'],
      tool_name: 'tool_combinations',
      tool_type: 'guide'
    }
  }
];

// Add all documentation to the prompt library
async function addToolDocumentation() {
  console.log('Adding tool documentation to prompt library...\n');
  
  let successCount = 0;
  let errorCount = 0;
  
  for (const doc of toolDocumentation) {
    try {
      const result = await memoryOperations.addSystemPromptFragment(
        doc.fragment,
        doc.metadata
      );
      
      console.log(`✅ Added: ${doc.metadata.tool_name} (${doc.metadata.tool_type})`);
      successCount++;
    } catch (error) {
      console.error(`❌ Failed to add ${doc.metadata.tool_name}: ${error.message}`);
      errorCount++;
    }
  }
  
  console.log(`\n📊 Summary:`);
  console.log(`   Successfully added: ${successCount}`);
  console.log(`   Errors: ${errorCount}`);
  console.log(`   Total: ${toolDocumentation.length}`);
  
  // Also create a summary document
  const summaryDoc = {
    fragment: `# Available Tools Summary

**Python Tools** (in python-tools/):
- search_products: Search with Shopify query syntax
- get_product: Get product by ID/handle/SKU
- create_product: Create simple products
- create_full_product: Create products with variants
- update_pricing: Update prices
- bulk_price_update: Bulk price updates
- manage_tags: Add/remove tags
- update_status: Change product status
- create_combo: Create bundle products
- create_open_box: Create open box variants
- manage_inventory_policy: Control overselling
- memory_operations: Search/retrieve memories
- update_conversation_topic: Update conversation title
- graphql_query: Custom GraphQL queries
- graphql_mutation: Custom GraphQL mutations
- pplx: Perplexity AI research

**Orchestrator Tools**:
- bash: Execute bash commands safely
- report_task_progress: Update task status
- mark_task_complete: Complete tasks
- File operations (via bash)

**Tool Locations**:
- Python tools: /home/pranav/espressobot/frontend/python-tools/
- Tool definitions: server/custom-tools-definitions.js
- Extended tools: server/custom-tools-definitions-extended.js
- Bash tool: server/tools/bash-tool-simple.js
- Task tracking: server/tools/task-tracking-tools.js`,
    metadata: {
      category: 'tools',
      agent_type: 'all',
      priority: 'high',
      tags: ['summary', 'overview', 'all-tools'],
      tool_name: 'tools_summary',
      tool_type: 'guide'
    }
  };
  
  try {
    await memoryOperations.addSystemPromptFragment(
      summaryDoc.fragment,
      summaryDoc.metadata
    );
    console.log('\n✅ Added tools summary document');
  } catch (error) {
    console.error('❌ Failed to add summary:', error.message);
  }
  
  process.exit(errorCount > 0 ? 1 : 0);
}

// Run the script
addToolDocumentation().catch(console.error);