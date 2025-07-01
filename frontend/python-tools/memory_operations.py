#!/usr/bin/env python3
"""
Memory operations CLI for bash agents
Provides access to the local memory system with proper user ID handling
"""

import argparse
import json
import os
import sys
import sqlite3
from pathlib import Path

# Database path
DB_PATH = Path(__file__).parent.parent / 'server' / 'memory' / 'data' / 'espressobot_memory.db'

def get_user_id():
    """Get the current user ID from environment or default"""
    # Try to get from environment (set by bash orchestrator)
    user_id = os.environ.get('ESPRESSOBOT_USER_ID')
    if user_id:
        return f"user_{user_id}"
    
    # Try to get from global context (if available)
    conversation_id = os.environ.get('ESPRESSOBOT_CONVERSATION_ID')
    if conversation_id:
        # Default to user_2 for now (should be passed from orchestrator)
        return "user_2"
    
    # Default fallback
    return "user_2"

def search_memories(query, limit=10):
    """Search memories for the current user"""
    user_id = get_user_id()
    
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get all memories for the user
        cursor.execute("""
            SELECT id, content, metadata, created_at 
            FROM memories 
            WHERE user_id = ? 
            ORDER BY created_at DESC 
            LIMIT ?
        """, (user_id, limit))
        
        memories = []
        for row in cursor.fetchall():
            memory = {
                'id': row['id'],
                'memory': row['content'],
                'metadata': json.loads(row['metadata']) if row['metadata'] else {},
                'created_at': row['created_at']
            }
            
            # Simple keyword matching for now (since embeddings require OpenAI)
            if query.lower() in memory['memory'].lower():
                memories.append(memory)
        
        conn.close()
        
        return {
            'success': True,
            'user_id': user_id,
            'memories': memories[:limit],
            'count': len(memories)
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'user_id': user_id
        }

def get_all_memories(limit=100):
    """Get all memories for the current user"""
    user_id = get_user_id()
    
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
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
                'memory': row['content'],
                'metadata': json.loads(row['metadata']) if row['metadata'] else {},
                'created_at': row['created_at']
            })
        
        conn.close()
        
        return {
            'success': True,
            'user_id': user_id,
            'memories': memories,
            'count': len(memories)
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'user_id': user_id
        }

def add_memory(content, metadata=None):
    """Add a memory for the current user (requires JS backend for embeddings)"""
    return {
        'success': False,
        'error': 'Adding memories requires the JavaScript backend for embedding generation. Use the memory tool through the orchestrator instead.',
        'user_id': get_user_id()
    }

def main():
    parser = argparse.ArgumentParser(description='Memory operations for EspressoBot')
    
    subparsers = parser.add_subparsers(dest='operation', help='Operation to perform')
    
    # Search operation
    search_parser = subparsers.add_parser('search', help='Search memories')
    search_parser.add_argument('query', help='Search query')
    search_parser.add_argument('--limit', type=int, default=10, help='Maximum results')
    
    # Get all operation
    getall_parser = subparsers.add_parser('get_all', help='Get all memories')
    getall_parser.add_argument('--limit', type=int, default=100, help='Maximum results')
    
    # Add operation (will show error)
    add_parser = subparsers.add_parser('add', help='Add a memory')
    add_parser.add_argument('content', help='Memory content')
    add_parser.add_argument('--metadata', type=json.loads, help='JSON metadata')
    
    args = parser.parse_args()
    
    if not args.operation:
        parser.print_help()
        sys.exit(1)
    
    # Execute the operation
    if args.operation == 'search':
        result = search_memories(args.query, args.limit)
    elif args.operation == 'get_all':
        result = get_all_memories(args.limit)
    elif args.operation == 'add':
        result = add_memory(args.content, args.metadata)
    else:
        result = {'success': False, 'error': f'Unknown operation: {args.operation}'}
    
    # Output as JSON
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()