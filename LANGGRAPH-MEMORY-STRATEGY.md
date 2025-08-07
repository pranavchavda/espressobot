# LangGraph Memory Management & Prompt Chunking Strategy

## Overview

This document outlines how we'll handle memory management and system prompt chunking in the LangGraph backend, based on the sophisticated system from the frontend OpenAI SDK implementation.

## Current Frontend System Analysis

### 1. **Memory System Architecture**
The frontend uses a sophisticated local memory system:

```
Frontend Memory Components:
├── SQLite Database (espressobot_memory.db)
├── OpenAI Embeddings (text-embedding-3-small)
├── Semantic Search (cosine similarity)
├── Intelligent Extraction (GPT-4o-mini)
└── Strong Deduplication (4 layers)
```

**Key Features:**
- **User Isolation**: Each user has separate memory space (`user_{id}`)
- **Semantic Search**: ~200ms searches with configurable threshold (0.1 default)
- **Deduplication**: Exact, fuzzy (90%), key phrase, and semantic (85%) matching
- **Fact Extraction**: 2 facts per message exchange via GPT-4o-mini
- **No API Limits**: Local SQLite eliminates Mem0's 1000/month limit

### 2. **Tiered Context Building**
The frontend uses a sophisticated tiered context system:

```javascript
// Three context levels based on task complexity
├── Core Context (minimal, fast)
│   ├── Top-5 memories
│   ├── Last 3 conversation turns
│   └── Essential business rules
├── Standard Context (balanced)
│   ├── Top-10 memories
│   ├── Last 5 conversation turns
│   └── Relevant prompt fragments
└── Full Context (comprehensive)
    ├── Top-20 memories
    ├── All conversation history
    └── Complete business rules
```

### 3. **Prompt Chunking & Management**
The frontend implements sophisticated prompt management:

- **Prompt Fragment Library**: Stored in SQLite with categories and priorities
- **Dynamic Assembly**: Fragments selected based on task keywords
- **Token Limits**: Core (5 fragments), Standard (10), Full (20)
- **Compression**: Older conversation turns summarized via GPT-4o-mini
- **Adaptive Context**: Context expands/contracts based on task needs

## LangGraph Implementation Strategy

### Phase 1: Memory System Integration

#### 1.1 Direct SQLite Integration
```python
# /langgraph-backend/app/memory/memory_manager.py
import sqlite3
import asyncio
from typing import List, Dict, Optional
import numpy as np
from openai import AsyncOpenAI

class MemoryManager:
    def __init__(self):
        # Use the SAME SQLite database as frontend
        self.db_path = "/home/pranav/espressobot/frontend/server/memory/data/espressobot_memory.db"
        self.client = AsyncOpenAI()
        
    async def search(self, query: str, user_id: str, limit: int = 10) -> List[Dict]:
        """Semantic search using existing embeddings"""
        # Generate embedding for query
        embedding = await self._get_embedding(query)
        
        # Search using cosine similarity
        conn = sqlite3.connect(self.db_path)
        # ... SQL query with vector similarity
        
    async def add(self, content: str, user_id: str, metadata: Dict = None):
        """Add memory with deduplication"""
        # Check for duplicates
        if await self._is_duplicate(content, user_id):
            return
        
        # Generate embedding
        embedding = await self._get_embedding(content)
        
        # Store in SQLite
        # ...
```

#### 1.2 State Integration
```python
# Enhance GraphState to include memory
class GraphState(TypedDict):
    # ... existing fields ...
    
    # Memory management
    memory_context: Optional[List[Dict]]  # Retrieved memories
    memory_to_add: Optional[List[str]]    # Facts to store
    
    # Context management
    context_tier: str  # "core", "standard", "full"
    prompt_fragments: Optional[List[Dict]]
```

### Phase 2: Tiered Context Builder

#### 2.1 Python Implementation
```python
# /langgraph-backend/app/context/tiered_context_builder.py
from enum import Enum
from typing import Dict, List, Optional

class ContextTier(Enum):
    CORE = "core"
    STANDARD = "standard"  
    FULL = "full"

class TieredContextBuilder:
    def __init__(self, memory_manager: MemoryManager):
        self.memory_manager = memory_manager
        
    async def build_context(
        self,
        task: str,
        user_id: str,
        conversation_history: List[BaseMessage],
        tier: ContextTier = ContextTier.STANDARD
    ) -> Dict:
        """Build tiered context based on complexity"""
        
        context = {
            "tier": tier.value,
            "memories": [],
            "conversation": [],
            "prompt_fragments": [],
            "business_rules": []
        }
        
        # Memory limits based on tier
        memory_limits = {
            ContextTier.CORE: 5,
            ContextTier.STANDARD: 10,
            ContextTier.FULL: 20
        }
        
        # Fetch memories
        context["memories"] = await self.memory_manager.search(
            task, user_id, limit=memory_limits[tier]
        )
        
        # Handle conversation history
        if tier == ContextTier.CORE:
            # Only last 3 turns
            context["conversation"] = conversation_history[-3:]
        elif tier == ContextTier.STANDARD:
            # Last 5 turns + summary of older
            context["conversation"] = await self._compress_history(
                conversation_history, keep_recent=5
            )
        else:  # FULL
            # All history with intelligent compression
            context["conversation"] = await self._compress_history(
                conversation_history, keep_recent=10
            )
        
        # Add prompt fragments
        context["prompt_fragments"] = await self._get_prompt_fragments(
            task, tier
        )
        
        return context
```

#### 2.2 Complexity Analysis
```python
# /langgraph-backend/app/context/complexity_analyzer.py
class ComplexityAnalyzer:
    def analyze(self, task: str, state: GraphState) -> ContextTier:
        """Determine context tier based on task complexity"""
        
        complexity_score = 0
        task_lower = task.lower()
        
        # Bulk operations need more context
        if any(kw in task_lower for kw in ['bulk', 'all', 'multiple', 'batch']):
            complexity_score += 3
            
        # Complex operations
        if any(kw in task_lower for kw in ['create', 'update', 'migrate', 'analyze']):
            complexity_score += 2
            
        # Simple queries need minimal context
        if any(kw in task_lower for kw in ['what', 'show', 'list', 'find']):
            complexity_score += 1
            
        # Map to tier
        if complexity_score <= 2:
            return ContextTier.CORE
        elif complexity_score <= 4:
            return ContextTier.STANDARD
        else:
            return ContextTier.FULL
```

### Phase 3: Prompt Assembly & Chunking

#### 3.1 Dynamic Prompt Assembly
```python
# /langgraph-backend/app/prompts/prompt_assembler.py
class PromptAssembler:
    def __init__(self):
        self.base_prompts = {}  # Agent-specific base prompts
        self.fragment_library = {}  # Reusable fragments
        
    def assemble_prompt(
        self,
        agent_name: str,
        context: Dict,
        include_sections: List[str] = None
    ) -> str:
        """Dynamically assemble prompt based on context"""
        
        prompt_parts = []
        
        # 1. Base agent prompt
        prompt_parts.append(self.base_prompts[agent_name])
        
        # 2. User context (if available)
        if context.get("user_profile"):
            prompt_parts.append(self._build_user_section(context["user_profile"]))
        
        # 3. Memory context
        if context.get("memories"):
            prompt_parts.append(self._build_memory_section(context["memories"]))
        
        # 4. Conversation summary
        if context.get("conversation"):
            prompt_parts.append(self._build_conversation_section(context["conversation"]))
        
        # 5. Business rules (if needed)
        if "business_rules" in include_sections:
            prompt_parts.append(self._build_rules_section(context.get("business_rules", [])))
        
        # 6. Task-specific fragments
        if context.get("prompt_fragments"):
            prompt_parts.append(self._build_fragments_section(context["prompt_fragments"]))
        
        return "\n\n".join(prompt_parts)
```

#### 3.2 Token Management
```python
# /langgraph-backend/app/prompts/token_manager.py
import tiktoken

class TokenManager:
    def __init__(self, model: str = "gpt-4"):
        self.encoder = tiktoken.encoding_for_model(model)
        self.limits = {
            "core": 4000,      # Small, fast contexts
            "standard": 8000,  # Balanced
            "full": 16000      # Comprehensive
        }
        
    def count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        return len(self.encoder.encode(text))
        
    def truncate_to_limit(self, text: str, limit: int) -> str:
        """Truncate text to token limit"""
        tokens = self.encoder.encode(text)
        if len(tokens) <= limit:
            return text
        
        # Truncate and decode
        truncated = tokens[:limit]
        return self.encoder.decode(truncated)
        
    def optimize_prompt(self, prompt: str, tier: str) -> str:
        """Optimize prompt to fit within tier limits"""
        limit = self.limits[tier]
        current = self.count_tokens(prompt)
        
        if current <= limit:
            return prompt
            
        # Progressive reduction strategies
        # 1. Remove examples
        # 2. Compress descriptions
        # 3. Remove optional sections
        return self.truncate_to_limit(prompt, limit)
```

### Phase 4: Integration with Agents

#### 4.1 Enhanced Base Agent
```python
# /langgraph-backend/app/agents/base.py
class BaseAgent:
    def __init__(self):
        self.memory_manager = MemoryManager()
        self.context_builder = TieredContextBuilder(self.memory_manager)
        self.prompt_assembler = PromptAssembler()
        self.token_manager = TokenManager()
        
    async def process(self, state: GraphState) -> GraphState:
        """Process with memory and context management"""
        
        # 1. Analyze complexity
        tier = self.complexity_analyzer.analyze(
            state["messages"][-1].content,
            state
        )
        
        # 2. Build tiered context
        context = await self.context_builder.build_context(
            task=state["messages"][-1].content,
            user_id=state.get("user_id"),
            conversation_history=state["messages"],
            tier=tier
        )
        
        # 3. Assemble prompt
        system_prompt = self.prompt_assembler.assemble_prompt(
            agent_name=self.name,
            context=context,
            include_sections=self._get_required_sections(tier)
        )
        
        # 4. Optimize for token limits
        system_prompt = self.token_manager.optimize_prompt(
            system_prompt,
            tier.value
        )
        
        # 5. Execute with context
        response = await self._execute_with_context(
            state["messages"][-1].content,
            system_prompt,
            context
        )
        
        # 6. Extract memories from response
        if self.should_extract_memories:
            memories = await self._extract_memories(
                state["messages"][-1].content,
                response
            )
            state["memory_to_add"] = memories
        
        return state
```

#### 4.2 Memory Persistence Node
```python
# /langgraph-backend/app/nodes/memory_node.py
async def persist_memories(state: GraphState) -> GraphState:
    """Node to persist extracted memories"""
    
    if state.get("memory_to_add") and state.get("user_id"):
        memory_manager = MemoryManager()
        
        for memory in state["memory_to_add"]:
            await memory_manager.add(
                content=memory,
                user_id=state["user_id"],
                metadata={
                    "conversation_id": state.get("conversation_id"),
                    "agent": state.get("last_agent"),
                    "timestamp": datetime.now().isoformat()
                }
            )
        
        # Clear after persisting
        state["memory_to_add"] = None
    
    return state
```

## Implementation Roadmap

### Week 1: Core Memory System
1. **Day 1-2**: Set up SQLite integration with existing database
2. **Day 3-4**: Implement embedding generation and semantic search
3. **Day 5**: Add deduplication logic and memory extraction

### Week 2: Context Management
1. **Day 1-2**: Build tiered context builder
2. **Day 3-4**: Implement prompt assembly and chunking
3. **Day 5**: Add token optimization and management

### Week 3: Integration & Testing
1. **Day 1-2**: Integrate with all agents
2. **Day 3-4**: Add memory persistence workflow
3. **Day 5**: Performance testing and optimization

## Key Benefits

### 1. **Shared Memory with Frontend**
- Same SQLite database ensures consistency
- Memories persist across frontend/backend transitions
- No synchronization issues

### 2. **Intelligent Context Management**
- Automatic tier selection based on complexity
- Token-optimized prompts prevent overruns
- Progressive context expansion as needed

### 3. **Performance Optimization**
- Core tier for simple queries (< 500ms)
- Cached embeddings reduce API calls
- Async operations throughout

### 4. **Scalability**
- Fragment library grows over time
- Memories improve with usage
- Context compression prevents bloat

## Configuration

### Environment Variables
```bash
# Memory System
OPENAI_API_KEY=sk-...  # For embeddings
MEMORY_DB_PATH=/home/pranav/espressobot/frontend/server/memory/data/espressobot_memory.db

# Context Tiers
DEFAULT_CONTEXT_TIER=standard
MAX_TOKEN_LIMIT=16000

# Memory Extraction
EXTRACT_MEMORIES=true
MEMORIES_PER_EXCHANGE=2
```

### Database Schema (Existing)
```sql
-- Already exists in frontend SQLite
CREATE TABLE memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    memory TEXT NOT NULL,
    embedding BLOB,  -- 1536-dim vector
    metadata TEXT,    -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE prompt_fragments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT,
    priority INTEGER,
    content TEXT,
    tags TEXT,  -- JSON array
    embedding BLOB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Migration Notes

### From Frontend to LangGraph
1. **Keep using same SQLite database** - No data migration needed
2. **Reuse embedding format** - Same OpenAI text-embedding-3-small
3. **Port deduplication logic** - Critical for quality
4. **Maintain user isolation** - Same `user_{id}` format

### Key Differences
- **Async throughout** - LangGraph is async-first
- **State-based** - Memory in GraphState vs function params
- **Node-based persistence** - Dedicated node vs inline saves
- **Python native** - No JavaScript/Python boundary

## Success Metrics

### Performance Targets
- Memory search: < 200ms (matching frontend)
- Context building: < 500ms for standard tier
- Token optimization: 30-40% reduction from raw
- Memory extraction: < 1s per exchange

### Quality Metrics
- Deduplication rate: > 90% (prevent memory spam)
- Relevance score: > 0.75 for retrieved memories
- Context hit rate: > 80% (useful context retrieved)
- Token efficiency: < 8K average for standard tier

## Conclusion

This strategy brings the sophisticated memory and context management from the frontend to the LangGraph backend, ensuring:
1. **Continuity**: Same database, same user experience
2. **Intelligence**: Tiered contexts adapt to task complexity
3. **Efficiency**: Token optimization reduces costs
4. **Scalability**: System improves with usage

The implementation is designed to be incremental, allowing us to start with basic memory integration and progressively add sophistication while maintaining backward compatibility with the frontend system.