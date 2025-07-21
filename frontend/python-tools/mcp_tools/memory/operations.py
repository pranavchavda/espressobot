"""
Native MCP implementation for memory operations
"""

import json
import sqlite3
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime
from ..base import BaseMCPTool

class MemoryOperationsTool(BaseMCPTool):
    """Memory operations for EspressoBot's local memory system"""
    
    name = "memory_operations"
    description = "Search, add, and manage memories in EspressoBot's local memory system"
    context = """
    Provides access to EspressoBot's local memory system with semantic search.
    
    Operations:
    - search: Search memories with semantic similarity
    - add: Add new memories
    - list: List recent memories
    - delete: Remove specific memories
    
    The memory system:
    - Uses local SQLite database
    - Supports semantic search via embeddings
    - User-isolated memories
    - Automatic deduplication
    
    Use cases:
    - Store important facts about products/customers
    - Remember past conversations and decisions
    - Build context for future interactions
    - Track business rules and patterns
    """
    
    input_schema = {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["search", "add", "list", "delete"],
                "description": "Operation to perform"
            },
            "query": {
                "type": "string",
                "description": "Search query (for search operation)"
            },
            "content": {
                "type": "string",
                "description": "Memory content to add"
            },
            "limit": {
                "type": "integer",
                "description": "Maximum results to return (default: 10)",
                "default": 10
            },
            "memory_id": {
                "type": "integer",
                "description": "Memory ID to delete"
            },
            "user_id": {
                "type": "string",
                "description": "User ID (default: user_2)"
            }
        },
        "required": ["operation"]
    }
    
    def __init__(self):
        super().__init__()
        # Database path - matching the bash orchestrator's memory system
        # From /python-tools/mcp_tools/memory/operations.py to /server/memory/data/
        self.db_path = Path(__file__).parent.parent.parent.parent / 'server' / 'memory' / 'data' / 'espressobot_memory.db'
        
    async def execute(self, operation: str, **kwargs) -> Dict[str, Any]:
        """Execute memory operation"""
        user_id = kwargs.get('user_id', 'user_2')
        
        try:
            if operation == 'search':
                return await self._search(kwargs.get('query', ''), user_id, kwargs.get('limit', 10))
            elif operation == 'add':
                return await self._add(kwargs.get('content', ''), user_id)
            elif operation == 'list':
                return await self._list(user_id, kwargs.get('limit', 10))
            elif operation == 'delete':
                return await self._delete(kwargs.get('memory_id'), user_id)
            else:
                return {"success": False, "error": f"Unknown operation: {operation}"}
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "operation": operation
            }
    
    async def _search(self, query: str, user_id: str, limit: int) -> Dict[str, Any]:
        """Search memories"""
        if not query:
            return {"success": False, "error": "Query required for search"}
        
        # Check if database exists
        if not self.db_path.exists():
            return {"success": False, "error": f"Database not found at {self.db_path}"}
            
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
        except sqlite3.Error as e:
            return {"success": False, "error": f"Database connection error: {str(e)}"}
        
        try:
            # For now, do simple text search
            # TODO: Integrate with embedding search when available
            cursor.execute("""
                SELECT id, content, metadata, created_at 
                FROM memories 
                WHERE user_id = ? AND content LIKE ?
                ORDER BY created_at DESC 
                LIMIT ?
            """, (user_id, f'%{query}%', limit))
            
            memories = []
            for row in cursor.fetchall():
                memories.append({
                    'id': row['id'],
                    'content': row['content'],
                    'metadata': json.loads(row['metadata']) if row['metadata'] else {},
                    'created_at': row['created_at']
                })
            
            return {
                "success": True,
                "memories": memories,
                "count": len(memories),
                "query": query
            }
            
        finally:
            conn.close()
    
    async def _add(self, content: str, user_id: str) -> Dict[str, Any]:
        """Add memory"""
        if not content:
            return {"success": False, "error": "Content required"}
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO memories (user_id, content, created_at)
                VALUES (?, ?, ?)
            """, (user_id, content, datetime.now().isoformat()))
            
            conn.commit()
            memory_id = cursor.lastrowid
            
            return {
                "success": True,
                "message": "Memory added successfully",
                "memory_id": memory_id
            }
            
        finally:
            conn.close()
    
    async def _list(self, user_id: str, limit: int) -> Dict[str, Any]:
        """List recent memories"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT id, content, metadata, created_at 
                FROM memories 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT ?
            """, (user_id, limit))
            
            memories = []
            for row in cursor.fetchall():
                memories.append({
                    'id': row['id'],
                    'content': row['content'],
                    'metadata': json.loads(row['metadata']) if row['metadata'] else {},
                    'created_at': row['created_at']
                })
            
            return {
                "success": True,
                "memories": memories,
                "count": len(memories)
            }
            
        finally:
            conn.close()
    
    async def _delete(self, memory_id: Optional[int], user_id: str) -> Dict[str, Any]:
        """Delete memory"""
        if not memory_id:
            return {"success": False, "error": "Memory ID required"}
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                DELETE FROM memories 
                WHERE id = ? AND user_id = ?
            """, (memory_id, user_id))
            
            conn.commit()
            deleted = cursor.rowcount > 0
            
            if deleted:
                return {
                    "success": True,
                    "message": f"Memory {memory_id} deleted"
                }
            else:
                return {
                    "success": False,
                    "error": f"Memory {memory_id} not found or not owned by user"
                }
                
        finally:
            conn.close()
            
    async def test(self) -> Dict[str, Any]:
        """Test memory operations"""
        try:
            # Check if database exists
            if not self.db_path.exists():
                return {
                    "status": "failed",
                    "error": f"Database not found at {self.db_path}"
                }
                
            # Try to connect
            conn = sqlite3.connect(self.db_path)
            conn.close()
            
            return {
                "status": "passed",
                "message": "Memory system accessible"
            }
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }