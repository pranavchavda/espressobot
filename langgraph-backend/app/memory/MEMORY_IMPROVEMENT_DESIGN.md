# Memory System Improvement Design

## Current Issues
1. **Low-quality memories extracted**: Many memories are task-specific and ephemeral
2. **No relevance decay**: Old memories persist forever without losing importance
3. **No usage tracking**: We don't know which memories are actually helpful
4. **No feedback loop**: System doesn't learn from memory effectiveness

## Proposed Architecture

### 1. Enhanced Memory Model

```python
@dataclass
class EnhancedMemory:
    # Core fields (existing)
    id: str
    user_id: str
    content: str
    embedding: List[float]
    category: str
    importance_score: float
    created_at: datetime
    updated_at: datetime
    
    # New tracking fields
    access_count: int = 0              # How many times accessed
    last_accessed_at: datetime = None  # When last accessed
    usefulness_score: float = 0.5      # Did it help in conversations?
    decay_rate: float = 0.01           # How fast it decays
    
    # Memory quality indicators
    is_ephemeral: bool = False        # Short-term/task-specific
    confidence_score: float = 0.5     # Extraction confidence
    verification_status: str = "unverified"  # verified/unverified/rejected
    
    # Context tracking
    source_conversation_id: str = None
    source_message_ids: List[str] = []
    used_in_conversations: List[str] = []
    
    def calculate_effective_importance(self) -> float:
        """Calculate importance considering decay and usage"""
        # Time decay factor
        days_old = (datetime.utcnow() - self.created_at).days
        time_decay = math.exp(-self.decay_rate * days_old)
        
        # Usage boost factor
        usage_boost = 1 + (0.1 * min(self.access_count, 10))
        
        # Usefulness multiplier
        usefulness_mult = 0.5 + self.usefulness_score
        
        # Combined score
        return self.importance_score * time_decay * usage_boost * usefulness_mult
```

### 2. Improved Memory Extraction

#### A. Multi-Stage Extraction Pipeline

```python
class ImprovedMemoryExtractor:
    async def extract_memories(self, messages: List[BaseMessage]) -> List[Memory]:
        # Stage 1: Initial extraction with quality focus
        raw_memories = await self._extract_raw_memories(messages)
        
        # Stage 2: Classify ephemerality
        classified = await self._classify_ephemerality(raw_memories)
        
        # Stage 3: Validate and score confidence
        validated = await self._validate_memories(classified)
        
        # Stage 4: Deduplicate and merge
        final = await self._deduplicate_and_merge(validated)
        
        return final
```

#### B. Better Extraction Prompts

```python
EXTRACTION_PROMPT = """
Analyze this conversation and extract ONLY high-value, long-term memories.

EXTRACT memories that are:
✓ Personal preferences that will persist ("I prefer dark roast coffee")
✓ Important facts about the user ("I work at Google", "I have two kids")
✓ Recurring problems or needs ("I always struggle with X")
✓ Learned solutions that could apply again
✓ Business relationships and context

DO NOT EXTRACT:
✗ One-time tasks ("check today's sales")
✗ Temporary states ("currently looking at...")
✗ Actions taken ("user reviewed emails")
✗ Ephemeral data ("today's performance")

For each memory, provide:
- content: The memory itself (be specific)
- category: preferences|facts|problems|solutions|relationships|products
- importance: 0.1-1.0 (consider long-term value)
- is_ephemeral: true if this is task/time specific
- confidence: 0.1-1.0 (how certain this is valuable)
- reasoning: Why this memory matters long-term
"""
```

### 3. Memory Decay System

```python
class MemoryDecayManager:
    def __init__(self):
        self.base_decay_rate = 0.01  # Per day
        self.category_decay_rates = {
            "preferences": 0.005,  # Slow decay
            "facts": 0.008,
            "problems": 0.015,    # Medium decay
            "solutions": 0.012,
            "interactions": 0.02,  # Fast decay
            "general": 0.015
        }
    
    async def update_memory_scores(self):
        """Run daily to update all memory scores"""
        memories = await self.get_all_active_memories()
        
        for memory in memories:
            # Calculate decay
            effective_importance = memory.calculate_effective_importance()
            
            # Mark for archival if too low
            if effective_importance < 0.1:
                memory.status = "archived"
            
            # Boost if frequently accessed
            if memory.access_count > 5:
                memory.decay_rate *= 0.8  # Slow down decay
            
            await self.update_memory(memory)
```

### 4. Feedback Loop System

```python
class MemoryFeedbackLoop:
    async def track_memory_usage(self, 
                                  conversation_id: str,
                                  memories_provided: List[Memory],
                                  agent_response: str,
                                  user_feedback: Optional[str] = None):
        """Track which memories were useful"""
        
        # Implicit feedback: Did agent use the memory?
        used_memories = self._detect_memory_usage(
            memories_provided, 
            agent_response
        )
        
        for memory in memories_provided:
            memory.access_count += 1
            memory.last_accessed_at = datetime.utcnow()
            
            if memory in used_memories:
                memory.usefulness_score = min(1.0, memory.usefulness_score + 0.1)
                memory.used_in_conversations.append(conversation_id)
            else:
                memory.usefulness_score = max(0.0, memory.usefulness_score - 0.05)
        
        # Explicit feedback if provided
        if user_feedback:
            await self._process_user_feedback(user_feedback, memories_provided)
    
    def _detect_memory_usage(self, memories: List[Memory], response: str) -> List[Memory]:
        """Use NLP to detect if memories influenced the response"""
        used = []
        for memory in memories:
            # Check semantic similarity between memory and response
            if self._is_memory_reflected_in_response(memory, response):
                used.append(memory)
        return used
```

### 5. Memory Retrieval Optimization

```python
class OptimizedMemoryRetriever:
    async def get_relevant_memories(self, 
                                   query: str, 
                                   user_id: str,
                                   limit: int = 10) -> List[Memory]:
        """Get memories with smart filtering"""
        
        # Step 1: Semantic search
        candidates = await self.semantic_search(query, user_id, limit * 3)
        
        # Step 2: Filter by effective importance
        candidates = [m for m in candidates 
                     if m.calculate_effective_importance() > 0.2]
        
        # Step 3: Boost recent and frequently used
        candidates.sort(
            key=lambda m: (
                m.similarity_score * 0.4 +
                m.calculate_effective_importance() * 0.4 +
                (1.0 if m.last_accessed_at and 
                 (datetime.utcnow() - m.last_accessed_at).days < 7 
                 else 0.0) * 0.2
            ),
            reverse=True
        )
        
        return candidates[:limit]
```

### 6. Database Schema Updates

```sql
-- Add new columns to memories table
ALTER TABLE memories ADD COLUMN access_count INTEGER DEFAULT 0;
ALTER TABLE memories ADD COLUMN last_accessed_at TIMESTAMP;
ALTER TABLE memories ADD COLUMN usefulness_score FLOAT DEFAULT 0.5;
ALTER TABLE memories ADD COLUMN decay_rate FLOAT DEFAULT 0.01;
ALTER TABLE memories ADD COLUMN is_ephemeral BOOLEAN DEFAULT FALSE;
ALTER TABLE memories ADD COLUMN confidence_score FLOAT DEFAULT 0.5;
ALTER TABLE memories ADD COLUMN verification_status VARCHAR(20) DEFAULT 'unverified';
ALTER TABLE memories ADD COLUMN source_conversation_id VARCHAR(255);
ALTER TABLE memories ADD COLUMN used_in_conversations TEXT; -- JSON array

-- Create indexes for performance
CREATE INDEX idx_memories_effective_importance ON memories (
    user_id, 
    ((importance_score * exp(-(EXTRACT(EPOCH FROM (NOW() - created_at))/86400) * decay_rate)))
);
CREATE INDEX idx_memories_last_accessed ON memories (user_id, last_accessed_at DESC);
```

### 7. Implementation Phases

#### Phase 1: Improve Extraction Quality (Immediate)
- Update extraction prompts
- Add ephemerality classification
- Implement confidence scoring

#### Phase 2: Add Usage Tracking (Week 1)
- Track access counts and last accessed
- Implement memory usage detection
- Store conversation associations

#### Phase 3: Implement Decay System (Week 2)
- Add decay calculations
- Create scheduled decay job
- Implement archival threshold

#### Phase 4: Build Feedback Loop (Week 3)
- Detect memory usage in responses
- Update usefulness scores
- Create feedback API endpoints

#### Phase 5: Optimize Retrieval (Week 4)
- Implement smart filtering
- Add importance-based ranking
- Create memory analytics dashboard

### 8. Configuration

```python
class MemorySystemConfig:
    # Extraction settings
    MIN_CONFIDENCE_THRESHOLD = 0.3
    EPHEMERAL_AUTO_EXPIRE_DAYS = 7
    
    # Decay settings
    BASE_DECAY_RATE = 0.01
    MIN_IMPORTANCE_THRESHOLD = 0.1
    ARCHIVE_AFTER_DAYS_UNUSED = 30
    
    # Feedback settings
    USEFULNESS_INCREMENT = 0.1
    USEFULNESS_DECREMENT = 0.05
    
    # Retrieval settings
    SEMANTIC_WEIGHT = 0.4
    IMPORTANCE_WEIGHT = 0.4
    RECENCY_WEIGHT = 0.2
```

### 9. Monitoring & Analytics

```python
class MemoryAnalytics:
    async def get_memory_health_metrics(self, user_id: str):
        return {
            "total_memories": count,
            "active_memories": active_count,
            "archived_memories": archived_count,
            "avg_usefulness": avg_usefulness,
            "most_accessed": top_memories,
            "decay_distribution": decay_histogram,
            "extraction_quality": {
                "ephemeral_ratio": ephemeral/total,
                "avg_confidence": avg_confidence,
                "verified_ratio": verified/total
            }
        }
```

## Benefits

1. **Higher Quality Memories**: Only store truly valuable long-term information
2. **Automatic Cleanup**: Old, unused memories fade away naturally
3. **Learning System**: Gets better at identifying useful memories over time
4. **Performance**: Fewer, more relevant memories to search through
5. **User Trust**: System remembers what matters, forgets what doesn't

## Migration Strategy

1. Keep existing system running
2. Implement new extraction in parallel
3. Gradually migrate to new scoring system
4. A/B test memory quality improvements
5. Full cutover after validation

## Success Metrics

- Reduction in ephemeral memories: Target 70% reduction
- Increase in memory usefulness scores: Target 0.7 average
- Reduction in total memory count: Target 50% reduction
- Improvement in retrieval relevance: Target 30% improvement
- User satisfaction with memory accuracy: Target 90%