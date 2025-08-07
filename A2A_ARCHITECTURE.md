# A2A (Agent-to-Agent) Architecture for EspressoBot

## Architecture Comparison

### Current LangGraph Implementation
```
User → Router → Single Agent → User
```
- **Simple routing**: One agent per request
- **No collaboration**: Agents work in isolation
- **Limited context**: Single agent perspective

### A2A Orchestration Pattern
```
User → Orchestrator → Agent A ↔ Agent B ↔ Agent C → Orchestrator → User
                         ↑                    ↓
                    (requests help)      (provides data)
```

## Key Components

### 1. A2A Orchestrator (`orchestrator_a2a.py`)
- **Analyzes** request complexity
- **Routes** to primary agent
- **Coordinates** inter-agent communication
- **Synthesizes** multi-agent responses
- **Tracks** execution path for debugging

### 2. A2A State Management
```python
class A2AState:
    messages: List[BaseMessage]      # Conversation history
    primary_agent: str               # Lead agent for request
    current_agent: str               # Currently executing agent
    agent_requests: List[Dict]       # Help requests between agents
    agent_responses: Dict[str, Any]  # Collected responses
    execution_path: List[str]        # Audit trail
```

### 3. Agent Communication Protocol
```python
help_request = {
    "from": "products",        # Requesting agent
    "to": "pricing",           # Helper agent
    "need": "Get price for SKU-123",  # Specific need
    "context": {"skus": [...]} # Shared context
}
```

## Implementation Status

### ✅ Completed
- [x] A2A Orchestrator core implementation
- [x] Enhanced state management for A2A
- [x] Base class for A2A-enabled agents
- [x] Example Products A2A agent
- [x] Test endpoint for A2A pattern

### 🔄 In Progress
- [ ] Convert all agents to A2A pattern
- [ ] Multi-hop agent communication
- [ ] Response synthesis optimization

### 📋 TODO
- [ ] Integration with main API
- [ ] Performance optimization for multi-agent flows
- [ ] Caching for repeated A2A requests
- [ ] A2A request prioritization

## Example Flows

### Simple Request (Current)
```
User: "What's the price of Breville 870?"
Router → Pricing Agent → Response
```

### Complex Request (A2A)
```
User: "Show me the Breville 870 with current pricing and stock levels"

1. Orchestrator: Analyzes as complex request
2. Router: Primary agent = products
3. Products Agent: 
   - Gets product details
   - Requests help: "Need pricing for BES870XL"
4. Orchestrator: Routes to Pricing Agent
5. Pricing Agent: Returns price data
6. Products Agent: 
   - Requests help: "Need inventory for BES870XL"
7. Orchestrator: Routes to Inventory Agent
8. Inventory Agent: Returns stock levels
9. Products Agent: Completes with full data
10. Orchestrator: Synthesizes final response
```

## Benefits of A2A Pattern

### 1. **Comprehensive Responses**
- Multiple data sources in one response
- No need for multiple user queries
- Context preserved across agents

### 2. **Intelligent Collaboration**
- Agents recognize when they need help
- Automatic data enrichment
- Reduced user friction

### 3. **Maintainability**
- Clear execution paths
- Debuggable agent interactions
- Modular agent development

### 4. **Scalability**
- Add new agents without changing orchestration
- Agents can evolve independently
- Parallel execution possible for independent requests

## Configuration

### Environment Variables
```bash
DATABASE_URL=postgresql://espressobot:localdev123@localhost:5432/espressobot_dev
ANTHROPIC_API_KEY=your_api_key
```

### Testing A2A
```bash
# Test endpoint available at:
POST http://localhost:8000/test-a2a
{
  "message": "Show me Breville 870 with price and stock",
  "thread_id": "test-123"
}
```

## Migration Path

### Phase 1: Parallel Implementation
- Keep existing router-based system
- Add A2A orchestrator as alternative path
- Test with subset of queries

### Phase 2: Agent Migration
- Convert agents to support A2A gradually
- Maintain backward compatibility
- Add A2A capabilities without breaking existing flows

### Phase 3: Full Migration
- Route all complex queries through A2A
- Simple queries can still use direct routing
- Monitor and optimize performance

## Performance Considerations

### Latency
- A2A adds orchestration overhead
- Mitigate with:
  - Parallel agent execution where possible
  - Response caching
  - Early termination for simple requests

### Token Usage
- Multiple agent calls increase token usage
- Optimize with:
  - Focused agent prompts
  - Context pruning between agents
  - Result summarization

## Next Steps

1. **Immediate**: Test A2A orchestrator with real queries
2. **Short-term**: Convert high-value agents (Products, Pricing, Inventory)
3. **Long-term**: Full A2A migration with performance optimization