# Improved Memory Extraction System

## Key Improvements

### 1. **Per-Exchange Extraction**
- Processes conversations in exchanges (User message + Assistant response)
- Maximum 2 facts per exchange instead of 10 per conversation
- Handles long conversations better by breaking them down

### 2. **Better Extraction Rules**
- Extracts facts worth remembering long-term, not temporary states
- ALWAYS extracts when user says "remember this/that"
- Includes confirmed facts from assistant responses
- Focuses on: personal info, preferences, business facts, decisions

### 3. **System Entry Filtering**
Automatically filters out:
- Entries with `system_metrics` or `system_*` user IDs
- Content shorter than 10 characters
- JSON system logs (containing `"type":"context_usage"` etc.)

### 4. **Smart Priority System**
Priority extraction for:
- **Explicit requests**: "Remember that..." → Always extracted
- **Personal info**: Names, roles, birthdays, locations
- **Preferences**: "I prefer X", "My favorite is Y"
- **Business facts**: Company info, project names, metrics
- **Confirmed corrections**: When user confirms information

## Example Results

From a 4-exchange conversation, extracted 7 clean facts:
1. The user's name is Pranav.
2. Pranav works as a generalist at iDrinkCoffee.com.
3. Bruno is a customer support chatbot that handles customer inquiries.
4. Espressobot helps with store management.
5. The user prefers to review all changes before they are applied to production.
6. The user's favorite coffee is Ethiopian Yirgacheffe.
7. The CEO of iDrinkCoffee.com is Slawek Janicki.

From explicit remember request:
1. The company offers 15% discounts on all combo products.
2. The company offers 20% discounts on bulk orders over $500.

## Benefits

1. **Scalable**: Works with conversations of any length
2. **Focused**: 2 facts per exchange prevents information overload
3. **Clean**: No system logs or temporary states
4. **Intelligent**: Respects explicit "remember" requests
5. **Contextual**: Can extract confirmed facts from assistant responses

## Configuration

```javascript
// Use nano model for cost savings
await extractMemorySummary(conversation, { useNano: true });

// Or set globally
export USE_GPT_NANO_FOR_MEMORY=true
```

## What NOT Extracted
- Questions or requests: "Can you help with X?"
- Temporary states: "User is looking at Y"
- Process descriptions: "User is focused on gathering requirements"
- Unconfirmed suggestions: "You might want to try X"
- System logs and metrics

The system now creates a cleaner, more focused memory bank that truly captures what's worth remembering!