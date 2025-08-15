# Memory System Migration to PostgreSQL

This guide explains how to migrate the EspressoBot memory system from SQLite to PostgreSQL with pgvector support.

## 🎯 Overview

The migration script (`migrate_memory_to_postgres.py`) provides a comprehensive solution for:

1. **Database Setup**: Creates PostgreSQL schema with pgvector extension
2. **Data Migration**: Migrates existing SQLite memories (if any) to PostgreSQL  
3. **Schema Creation**: Sets up all necessary tables and indexes
4. **System Testing**: Validates the setup with sample operations
5. **Error Handling**: Provides detailed status messages and error reporting

## 📋 Prerequisites

### Database Requirements
- PostgreSQL 12+ with pgvector extension installed
- Database with appropriate permissions for creating tables and extensions

### Environment Variables
```bash
# Required
export DATABASE_URL='postgresql://username:password@host:port/database'
export OPENAI_API_KEY='your-openai-api-key'

# Optional
export MEMORY_TYPE='postgres'
```

### Python Dependencies
Ensure you're in the virtual environment with required packages:
```bash
source venv/bin/activate
pip install -r requirements.txt
```

## 🚀 Usage

### Basic Migration
```bash
python migrate_memory_to_postgres.py
```

### Available Options
```bash
# Drop and recreate existing tables (destroys data)
python migrate_memory_to_postgres.py --force-recreate

# Skip system testing after migration
python migrate_memory_to_postgres.py --skip-test

# Combined options
python migrate_memory_to_postgres.py --force-recreate --skip-test
```

### Testing Environment
```bash
# Test the setup before running migration
./test_migration.sh
```

## 📊 Database Schema

### Tables Created

1. **memories** - User-specific memories with embeddings
   - `id` (SERIAL PRIMARY KEY)
   - `user_id` (VARCHAR(255)) - User identifier
   - `content` (TEXT) - Memory content
   - `embedding` (vector(3072)) - OpenAI text-embedding-3-large
   - `metadata` (JSONB) - Additional structured data
   - `category` (VARCHAR(100)) - Memory category
   - `importance_score` (FLOAT) - Importance weight (0.0-1.0)
   - `access_count` (INTEGER) - Usage tracking
   - `last_accessed_at`, `created_at`, `updated_at` (TIMESTAMP)

2. **prompt_fragments** - Agent-specific context fragments
   - `id` (SERIAL PRIMARY KEY)
   - `category` (VARCHAR(100)) - Fragment category
   - `priority` (INTEGER) - Assembly priority
   - `content` (TEXT) - Fragment content
   - `tags` (TEXT[]) - Searchable tags
   - `embedding` (vector(3072)) - Content embedding
   - `agent_type` (VARCHAR(100)) - Target agent type
   - `context_tier` (VARCHAR(20)) - Context level (core/standard/full)
   - `is_active` (BOOLEAN) - Enable/disable flag
   - `created_at`, `updated_at` (TIMESTAMP)

3. **memory_duplicates** - Deduplication tracking
   - `id` (SERIAL PRIMARY KEY)
   - `original_id` (INTEGER) - Reference to original memory
   - `duplicate_hash` (VARCHAR(64)) - Content hash
   - `similarity_score` (FLOAT) - Similarity metric
   - `dedup_type` (VARCHAR(20)) - Detection method
   - `created_at` (TIMESTAMP)

4. **memory_analytics** - Usage analytics
   - `id` (SERIAL PRIMARY KEY)
   - `user_id` (VARCHAR(255)) - User identifier
   - `query_text` (TEXT) - Search query
   - `results_count` (INTEGER) - Number of results
   - `response_time_ms` (INTEGER) - Query performance
   - `context_tier` (VARCHAR(20)) - Context level used
   - `created_at` (TIMESTAMP)

### Indexes Created

#### Performance Indexes
- `memories_embedding_idx` - Vector similarity search (ivfflat)
- `memories_user_idx` - User-specific queries
- `memories_category_idx` - Category filtering
- `memories_importance_idx` - Importance sorting
- `memories_access_idx` - Access time sorting

#### Prompt Fragment Indexes
- `prompt_fragments_embedding_idx` - Fragment similarity search
- `prompt_fragments_category_idx` - Category filtering
- `prompt_fragments_agent_idx` - Agent-specific queries
- `prompt_fragments_tier_idx` - Context tier filtering
- `prompt_fragments_priority_idx` - Priority sorting

#### Analytics Indexes
- `memory_analytics_user_idx` - User analytics
- `memory_analytics_time_idx` - Time-based queries
- `memory_duplicates_hash_idx` - Hash lookups
- `memory_duplicates_original_idx` - Original reference queries

## 🔄 Migration Process

### Step 1: Database Connection
- Validates PostgreSQL connection
- Checks database permissions

### Step 2: pgvector Extension
- Verifies pgvector availability
- Creates extension if needed
- Tests vector operations

### Step 3: Schema Setup
- Drops existing tables (if `--force-recreate`)
- Creates new schema with all tables
- Sets up indexes and triggers
- Validates table creation

### Step 4: SQLite Migration
- Scans for existing SQLite database at:
  `/home/pranav/espressobot/frontend/server/memory/data/espressobot_memory.db`
- Extracts and migrates any existing memories
- Generates embeddings for migrated content
- Maps SQLite schema to PostgreSQL structure

### Step 5: Default Data
- Inserts default prompt fragments
- Creates system-level guidelines
- Sets up agent-specific contexts

### Step 6: System Testing
- Tests memory storage and retrieval
- Validates embedding generation
- Checks search functionality
- Verifies prompt assembly
- Tests deduplication system

## 📈 Expected Output

```
🚀 Starting memory system migration to PostgreSQL...
✅ PostgreSQL database connection successful
✅ pgvector extension is enabled
✅ Schema created successfully
Created tables: ['memories', 'memory_analytics', 'memory_duplicates', 'prompt_fragments']
SQLite database exists but is empty
✅ Inserted 7 default prompt fragments
🧪 Testing memory system operations...
✅ Test memory stored with ID: 1
✅ Memory search working: found 1 results
   Best match similarity: 0.856
✅ Embedding service working: 3072 dimensions
✅ Prompt assembly working: 1 memories, 2 fragments
✅ Memory stats: {'total_memories': 1, 'categories': 1, 'avg_importance': 0.8, 'total_accesses': 2, 'latest_memory': datetime(...)}
✅ Test data cleaned up
🎉 All memory system tests passed!
============================================================
Migration Summary:
  Memories migrated: 0
  Prompt fragments: 7
  Errors encountered: 0
============================================================
🎉 Migration completed successfully!
✅ Memory system is ready for use!
```

## ⚠️ Important Notes

### Data Safety
- **Backup your data** before running with `--force-recreate`
- The script preserves existing PostgreSQL data by default
- SQLite migration is non-destructive (original files unchanged)

### Performance Considerations
- pgvector indexes are created for optimal similarity search
- Connection pooling is configured for production use
- Embedding cache reduces OpenAI API calls

### Error Recovery
- Failed migrations can be re-run safely
- Partial migrations are rolled back automatically
- Detailed error logging helps debugging

## 🔧 Troubleshooting

### Common Issues

#### pgvector Extension Missing
```
❌ pgvector extension is not available in this PostgreSQL instance
```
**Solution**: Install pgvector extension:
```bash
# Ubuntu/Debian
sudo apt install postgresql-14-pgvector

# macOS with Homebrew
brew install pgvector

# From source
git clone --branch v0.5.1 https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install
```

#### Database Connection Failed
```
❌ Failed to connect to PostgreSQL: connection to server at "localhost", port 5432 failed
```
**Solution**: Verify DATABASE_URL format and PostgreSQL service:
```bash
# Check PostgreSQL status
systemctl status postgresql

# Test connection
psql $DATABASE_URL -c "SELECT version();"
```

#### OpenAI API Issues
```
❌ Failed to generate embedding: Incorrect API key provided
```
**Solution**: Verify OPENAI_API_KEY is set correctly:
```bash
echo $OPENAI_API_KEY
# Should show your API key starting with sk-
```

#### Insufficient Permissions
```
❌ permission denied to create extension "vector"
```
**Solution**: Grant appropriate permissions:
```sql
-- As superuser
GRANT ALL PRIVILEGES ON DATABASE your_db TO your_user;
-- Or grant specific permissions as needed
```

### Debug Mode
For detailed debugging, modify the logging level in the script:
```python
logging.basicConfig(level=logging.DEBUG)
```

## 🧪 Testing

### Manual Testing
```bash
# Test database connection
python -c "
import asyncio
import os
import asyncpg

async def test():
    conn = await asyncpg.connect(os.getenv('DATABASE_URL'))
    result = await conn.fetchrow('SELECT version()')
    print(f'PostgreSQL: {result[0]}')
    await conn.close()

asyncio.run(test())
"

# Test embeddings
python -c "
import asyncio
import os
from app.memory.embedding_service import get_embedding_service

async def test():
    service = get_embedding_service()
    result = await service.get_embedding('test')
    print(f'Embedding dimensions: {len(result.embedding)}')

asyncio.run(test())
"
```

### Integration Testing
```bash
# Run full memory system test
python test_memory_system.py
```

## 📚 Related Documentation

- [Memory System Architecture](MEMORY_SYSTEM.md)
- [API Documentation](README.md)
- [Testing Guide](TESTING_GUIDE.md)
- [pgvector Documentation](https://github.com/pgvector/pgvector)

## 🤝 Support

If you encounter issues:

1. Check the troubleshooting section above
2. Review the migration logs for specific error messages
3. Ensure all prerequisites are met
4. Test individual components separately

## 🔄 Rollback

To rollback to SQLite (if needed):

1. Set environment variable:
   ```bash
   export MEMORY_TYPE='sqlite'
   ```

2. The system will automatically use SQLite checkpointer

3. PostgreSQL data remains untouched for future use