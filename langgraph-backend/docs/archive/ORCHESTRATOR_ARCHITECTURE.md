# Orchestrator Architecture - The Original Vision

## Core Principle
**The orchestrator is the brain. Agents are just hands.**

## Flow Pattern
```
User → Orchestrator → Agent1 → Orchestrator → Agent2 → Orchestrator → ... → User
```

NOT:
```
User → Orchestrator → [Agent1, Agent2, Agent3] → Synthesis → User
```

## Key Concepts

### 1. Orchestrator Maintains All State
- The orchestrator remembers EVERYTHING from the conversation
- Product IDs, handles, previous searches, failed attempts - all stored
- Agents don't need memory because orchestrator provides context

### 2. Progressive Agent Calls
- Call ONE agent at a time
- Review the result
- Decide next action based on what was learned
- Provide refined context to next agent

### 3. Intelligent Context Provision
When calling an agent, orchestrator provides:
- Specific task ("Get product ID for Mazzer ZM Plus")
- Relevant context from previous attempts
- Hints and strategies if previous attempts failed
- Specific IDs/data from earlier in conversation

### 4. Course Correction
If an agent fails:
- Orchestrator doesn't give up
- It provides more specific instructions
- It suggests alternative approaches
- It can try a different agent

### 5. Cross-Turn Memory
- Orchestrator remembers findings across user messages
- No re-searching for already found items
- Builds a knowledge base throughout the conversation

## Example Flow

### Turn 1:
```
User: "Upload image to Mazzer ZM Plus"
Orchestrator → ProductAgent: "Get product ID for Mazzer ZM Plus"
ProductAgent: "0 products found"
Orchestrator → ProductAgent: "Search for 'Mazzer' with limit 100"
ProductAgent: "Found 2 variants: white (ID: 123), black (ID: 456)"
Orchestrator → MediaAgent: "Upload image to product 123"
MediaAgent: "Success"
Orchestrator → User: "Uploaded to white Mazzer ZM Plus"
```

### Turn 2:
```
User: "Delete it from the white one"
Orchestrator (knows ID 123 is white) → MediaAgent: "Delete image from product 123"
MediaAgent: "Success"
Orchestrator → User: "Deleted from white Mazzer ZM Plus"
```

## Implementation Requirements

### Orchestrator Needs:
1. **Conversation Memory**: Store all findings (product IDs, handles, etc.)
2. **Progressive Routing**: One agent at a time, evaluate, continue
3. **Context Builder**: Create specific context for each agent call
4. **Result Evaluator**: Determine if agent succeeded or needs help
5. **Strategy Generator**: Create alternative approaches when agents fail

### Agents Need:
1. **Simple Interface**: Receive task + context, return result
2. **No State Management**: Orchestrator handles all state
3. **Clear Responses**: Success/failure and what was found
4. **Tool Execution**: Focus on executing tools, not reasoning

## Benefits

1. **Smarter System**: Orchestrator can adapt based on intermediate results
2. **Better Debugging**: Can see exactly where things went wrong
3. **Efficient**: Don't call unnecessary agents if we have the info
4. **Contextual**: Each agent gets exactly what it needs to succeed
5. **Conversational**: Natural flow across multiple user turns

## Anti-Patterns to Avoid

❌ Calling all agents upfront  
❌ Agents maintaining their own state  
❌ Re-searching for already found items  
❌ Losing context between user messages  
❌ Agents trying to be too smart  

## The Golden Rule
**The orchestrator thinks. The agents do.**