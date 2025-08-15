# 🧪 Testing Guide for LangGraph Backend

## Quick Start Testing

### 1. Start the Server

Open a terminal and start the backend:

```bash
cd /home/pranav/espressobot/langgraph-backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

### 2. Test with Browser

Open your browser and visit:
- http://localhost:8000 - Should show: `{"message":"EspressoBot LangGraph Backend","status":"operational"}`
- http://localhost:8000/health - Should show: `{"status":"healthy"}`
- http://localhost:8000/docs - Interactive API documentation (Swagger UI)

### 3. Run Automated Tests

In a new terminal:

```bash
cd /home/pranav/espressobot/langgraph-backend
source venv/bin/activate

# Run all unit tests
pytest tests/ -v

# Run specific test categories
pytest tests/test_agents.py -v      # Agent tests
pytest tests/test_orchestrator.py -v # Orchestrator tests
pytest tests/test_api.py -v         # API endpoint tests

# Run the comprehensive test suite
python test_backend.py
```

### 4. Interactive Chat Testing

Start interactive mode to chat with the bot:

```bash
python test_backend.py --interactive
```

Try these prompts:
- "Hello!"
- "Find product SKU ESP-001"
- "What espresso machines do you have?"
- "Update the price to $50"
- "Show me grinders"
- "Check inventory"

Type `quit` to exit.

## Manual API Testing

### Using curl

```bash
# Test chat endpoint
curl -X POST http://localhost:8000/api/agent/message \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, I need help finding a coffee machine"}'

# List available agents
curl http://localhost:8000/api/agent/agents

# Test SSE streaming (will stream events)
curl -X POST http://localhost:8000/api/agent/sse \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{"message": "Tell me about your products"}'
```

### Using httpie (if installed)

```bash
# Simpler syntax with httpie
http POST localhost:8000/api/agent/message message="Hello"
http GET localhost:8000/api/agent/agents
```

### Using Python

```python
import httpx
import asyncio

async def test_chat():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/agent/message",
            json={"message": "Find espresso machines"}
        )
        print(response.json())

asyncio.run(test_chat())
```

## Testing SSE Streaming

The SSE endpoint streams responses in real-time. Test with:

```python
import httpx
import json

def test_sse():
    with httpx.stream(
        "POST",
        "http://localhost:8000/api/agent/sse",
        json={"message": "Tell me about coffee"},
        headers={"Accept": "text/event-stream"}
    ) as response:
        for line in response.iter_lines():
            if line.startswith("data: "):
                data = json.loads(line[6:])
                print(f"Agent: {data.get('agent')}")
                print(f"Message: {data.get('message')}")

test_sse()
```

## Test Scenarios

### 1. Agent Routing Test
Test that messages route to correct agents:

```json
// Should route to products agent
{"message": "Find product SKU ESP-001"}

// Should route to pricing agent  
{"message": "Update the price to $699"}

// Should route to inventory agent
{"message": "Check stock levels"}

// Should route to sales agent
{"message": "Start a sale campaign"}
```

### 2. Conversation Persistence
Test that conversations maintain context:

```json
// First message
{"message": "I'm looking for a grinder", "conversation_id": "test-123"}

// Follow-up (should remember context)
{"message": "What's the price range?", "conversation_id": "test-123"}
```

### 3. Error Handling
Test error scenarios:

```json
// Empty message
{"message": ""}

// Missing required fields
{}

// Very long message
{"message": "..." } // 10000+ characters
```

## Performance Testing

### Load Testing with Apache Bench

```bash
# Test 100 requests with 10 concurrent
ab -n 100 -c 10 -p request.json -T application/json \
   http://localhost:8000/api/agent/message
```

### Stress Testing with locust

Create `locustfile.py`:

```python
from locust import HttpUser, task, between

class ChatUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def send_message(self):
        self.client.post("/api/agent/message", json={
            "message": "Find a coffee machine"
        })

# Run: locust -H http://localhost:8000
```

## Debugging

### Check Server Logs

The server logs show:
- Incoming requests
- Agent routing decisions
- Errors and stack traces

### Enable Debug Mode

Set environment variable:
```bash
export LOG_LEVEL=DEBUG
uvicorn app.main:app --reload --log-level debug
```

### Test Individual Components

```python
# Test orchestrator directly
from app.orchestrator import Orchestrator
import asyncio

async def test():
    orch = Orchestrator()
    result = await orch.run("Find products")
    print(result)

asyncio.run(test())
```

## Expected Behavior

✅ **Working Features:**
- Server starts and responds to health checks
- All 9 agents are loaded and listed
- Messages route to appropriate agents
- SSE streaming endpoint responds
- Basic chat functionality works

⚠️ **Known Limitations (Phase 2):**
- MCP tools not yet connected (needs Phase 3)
- Agents respond with basic messages only
- No actual product data (needs MCP servers)
- Database persistence not fully integrated

## Next Steps

After Phase 2 testing is complete, Phase 3 will:
1. Connect real MCP servers from `frontend/python-tools`
2. Enable actual product searches
3. Implement full tool functionality
4. Add database persistence

## Troubleshooting

### Server won't start
```bash
# Check if port is in use
lsof -i :8000
# Kill any existing process
pkill -f uvicorn

# Reinstall dependencies
pip install -r requirements-simple.txt
```

### Import errors
```bash
# Ensure you're in the virtual environment
source venv/bin/activate
which python  # Should show venv path

# Reinstall missing packages
pip install langgraph-checkpoint-sqlite email-validator
```

### Database errors
```bash
# Reinitialize database
python -c "from app.database.session import init_db; import asyncio; asyncio.run(init_db())"
```