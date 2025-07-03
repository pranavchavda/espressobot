# Conversation Topic System

## Overview
The conversation topic system allows agents and the orchestrator to set and update a topic for each conversation. This helps provide context and maintain focus throughout the conversation.

## Features

### 1. Topic Storage
- **topic_title**: A concise title (max 200 characters) summarizing the conversation
- **topic_details**: Optional detailed description with context, goals, or important information

### 2. Automatic Context Injection
When a conversation has a topic set, it's automatically injected into:
- The context loading system for all agents
- The beginning of the formatted context before business rules

### 3. Topic Updates
Topics can be updated at any time during the conversation by:
- The main orchestrator using `update_conversation_topic` tool
- Bash agents using the same tool
- Python scripts using `/python-tools/update_conversation_topic.py`

## Usage

### For Orchestrator/Agents (JavaScript)
```javascript
// The tool is automatically available
await update_conversation_topic({
  topic_title: "Product Pricing Update",
  topic_details: "Updating prices for coffee products with holiday discounts"
});
```

### For Bash Agents (Python Tool)
```bash
# Using conversation ID from environment
python3 /home/pranav/espressobot/frontend/python-tools/update_conversation_topic.py 0 "Product Pricing Update" --details "Updating prices for coffee products"

# Using explicit conversation ID
python3 /home/pranav/espressobot/frontend/python-tools/update_conversation_topic.py 123 "Inventory Management"
```

### API Endpoint
```
PUT /api/conversations/:id/topic
{
  "topic_title": "Product Management Task",
  "topic_details": "Creating new coffee products and setting up preorders"
}
```

## Best Practices

1. **Set topics early**: Identify and set the topic as soon as the main goal is clear
2. **Keep titles concise**: Use clear, descriptive titles under 200 characters
3. **Add details for complex tasks**: Use topic_details for multi-step operations
4. **Update as needed**: If the conversation shifts focus, update the topic

## Integration Points

1. **Context Manager**: Automatically loads topic at the beginning of context
2. **Conversation API**: Returns topic with conversation data
3. **SSE Events**: Emits `topic_updated` event when topic changes
4. **Database**: Stored in `conversations` table

## Example Topics

- **Title**: "Bulk Price Update"
  **Details**: "Update prices for all Mahlkonig grinders with 10% discount"

- **Title**: "Preorder Product Creation"
  **Details**: "Create new CD2025 products with preorder tags and NIS shipping"

- **Title**: "Inventory Analysis"
  **Details**: "Analyze low stock products and generate reorder recommendations"