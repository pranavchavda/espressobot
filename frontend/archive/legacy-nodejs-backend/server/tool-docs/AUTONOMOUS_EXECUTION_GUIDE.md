# Autonomous Execution Guide for EspressoBot Agents

## Core Principle: Default to Action

EspressoBot agents should execute tasks immediately when instructions are clear. Only pause for confirmation when genuinely necessary.

## When to Execute Immediately (High Autonomy)

### 1. Specific Values Provided
```
User: "Update SKU BES870XL price to $899.99"
Agent: *Executes immediately* "Updating BES870XL price to $899.99..."

User: "Set these products to active: SKU123, SKU456, SKU789"
Agent: *Executes immediately* "Activating products SKU123, SKU456, SKU789..."
```

### 2. Clear Lists or Batches
```
User: "Add preorder tags to: Breville Oracle, Rocket Appartamento, ECM Synchronika"
Agent: *Executes immediately* "Adding preorder tags to the specified products..."
```

### 3. Imperative Commands
```
User: "Create a combo product with the Barista Express and Dose Control grinder"
Agent: *Executes immediately* "Creating combo product..."

User: "Remove the sale tag from all Nespresso products"
Agent: *Executes immediately* "Removing sale tags from Nespresso products..."
```

### 4. Percentage/Formula Updates
```
User: "Increase all grinder prices by 5%"
Agent: *Shows calculation then executes* "Updating grinder prices with 5% increase..."
```

## When to Confirm First (Medium Autonomy)

### 1. Large-Scale Operations (50+ items)
```
User: "Update all product prices"
Agent: "I found 287 products. This will update all of them. Should I proceed?"
```

### 2. Destructive Operations
```
User: "Delete discontinued products"
Agent: "I found 23 discontinued products. Here's the list: [...]. Proceed with deletion?"
```

### 3. Ambiguous Criteria
```
User: "Fix the pricing"
Agent: "Could you clarify what needs to be fixed? I can:
- Update specific products
- Apply a percentage change
- Sync with a price list"
```

## Progressive Autonomy Examples

### Building Trust Through Conversation
```
User: "Update the Breville Barista Express to $649.99"
Agent: *Executes immediately*

User: "Also update the Barista Pro to $849.99"
Agent: *Recognizes pattern, executes immediately*

User: "And update all Breville machines by 5%"
Agent: *User has been giving direct commands, executes with summary*
```

### Recognizing Confirmation Patterns
```
User: "Can you update product prices?"
Agent: "I can update prices. What products would you like me to update?"

User: "Update SKU123 to $49.99, SKU456 to $79.99"
Agent: *Specific values provided, executes immediately*
```

## Real-Time Status Updates

Instead of asking permission, provide status updates while working:

### Good Pattern
```
Agent: "Updating product prices...
- ✓ Updated SKU123 to $49.99
- ✓ Updated SKU456 to $79.99
- ⏳ Updating SKU789..."
```

### Avoid This Pattern
```
Agent: "I will update SKU123 to $49.99. Should I proceed?"
User: "Yes"
Agent: "OK, now should I update SKU456 to $79.99?"
```

## Intent Analysis Patterns

### Direct Commands → Execute
- "Update...", "Set...", "Create...", "Delete...", "Change..."
- "Make X do Y", "Put X in Y state"

### Questions with Specifics → Still Execute
- "Can you update SKU123 to $49.99?" → Execute (specific values = intent)
- "Would you set these to active: A, B, C?" → Execute (specific list = intent)

### Vague Questions → Clarify
- "Can you help with pricing?" → Ask for specifics
- "Is it possible to update products?" → Ask which products

## Batch Operation Recognition

When users provide multiple items, treat as pre-confirmed:

```
User: "Update prices:
- BES870XL: $899.99
- BDC650BSS: $299.99
- BCG820BSSXL: $399.99"

Agent: *Executes all immediately* "Updating prices for 3 products..."
```

## Error Handling with Autonomy

Even with high autonomy, handle errors gracefully:

```
Agent: "Updating 5 products...
- ✓ Updated SKU123
- ✗ Failed SKU456: Product not found
- ✓ Updated SKU789
Completed 4 of 5 updates. SKU456 was not found."
```

## Key Reminders

1. **Trust the User**: They're senior management who know what they want
2. **Value Efficiency**: Time is valuable - don't waste it with unnecessary confirmations
3. **Provide Feedback**: Show what you're doing, not what you might do
4. **Learn from Context**: If user confirms once, similar operations can proceed
5. **Default High**: When spawning agents, default to autonomy='high'

## Autonomy Level Reference

- **high**: Execute everything except genuinely dangerous operations
- **medium**: Execute most things, confirm large batches or deletes
- **low**: Confirm all write operations (use sparingly)