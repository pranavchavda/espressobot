#!/usr/bin/env python3
"""
Standalone scratchpad tool for MCP servers
Can be imported and used by any MCP server to provide scratchpad functionality
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any

# Path to the scratchpad file
SCRATCHPAD_FILE = Path(__file__).parent.parent / 'server' / 'data' / 'scratchpad.json'

def ensure_data_directory():
    """Ensure the data directory exists"""
    SCRATCHPAD_FILE.parent.mkdir(parents=True, exist_ok=True)

def load_scratchpad() -> Dict[str, Any]:
    """Load scratchpad data from file"""
    try:
        ensure_data_directory()
        with open(SCRATCHPAD_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Return empty scratchpad if file doesn't exist or is invalid
        return {
            'content': '',
            'entries': [],
            'last_updated': None,
            'created_at': datetime.now().isoformat()
        }

def save_scratchpad(data: Dict[str, Any]):
    """Save scratchpad data to file"""
    ensure_data_directory()
    data['last_updated'] = datetime.now().isoformat()
    with open(SCRATCHPAD_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def format_scratchpad_content(scratchpad: Dict[str, Any]) -> str:
    """Format scratchpad content for display"""
    if not scratchpad.get('content') and not scratchpad.get('entries'):
        return 'Scratchpad is empty'
    
    formatted = ''
    if scratchpad.get('content'):
        formatted += f"**Main Content:**\n{scratchpad['content']}\n\n"
    
    if scratchpad.get('entries'):
        formatted += '**Recent Entries:**\n'
        for i, entry in enumerate(scratchpad['entries'][-10:], 1):
            timestamp = datetime.fromisoformat(entry['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
            formatted += f"{i}. [{timestamp}] {entry['author']}: {entry['content']}\n"
    
    return formatted

async def scratchpad_read() -> Dict[str, Any]:
    """Read scratchpad content"""
    scratchpad = load_scratchpad()
    
    if not scratchpad.get('content') and not scratchpad.get('entries'):
        return {
            'success': True,
            'message': 'Scratchpad is empty',
            'data': scratchpad
        }
    
    return {
        'success': True,
        'message': 'Scratchpad content retrieved',
        'data': scratchpad,
        'formatted': format_scratchpad_content(scratchpad)
    }

async def scratchpad_write(content: str) -> Dict[str, Any]:
    """Write content to scratchpad"""
    if not content:
        return {
            'success': False,
            'message': 'Content is required for write action'
        }
    
    scratchpad = load_scratchpad()
    scratchpad['content'] = content
    save_scratchpad(scratchpad)
    
    return {
        'success': True,
        'message': 'Scratchpad content updated',
        'data': scratchpad
    }

async def scratchpad_append(content: str) -> Dict[str, Any]:
    """Append content to scratchpad"""
    if not content:
        return {
            'success': False,
            'message': 'Content is required for append action'
        }
    
    scratchpad = load_scratchpad()
    scratchpad['content'] = (scratchpad.get('content', '') + '\n' + content).strip()
    save_scratchpad(scratchpad)
    
    return {
        'success': True,
        'message': 'Content appended to scratchpad',
        'data': scratchpad
    }

async def scratchpad_add_entry(content: str, author: str = 'unknown') -> Dict[str, Any]:
    """Add an entry to scratchpad"""
    if not content:
        return {
            'success': False,
            'message': 'Content is required for add_entry action'
        }
    
    scratchpad = load_scratchpad()
    if 'entries' not in scratchpad:
        scratchpad['entries'] = []
    
    entry = {
        'content': content,
        'author': author,
        'timestamp': datetime.now().isoformat(),
        'id': len(scratchpad['entries']) + 1
    }
    
    scratchpad['entries'].append(entry)
    
    # Keep only last 50 entries to prevent unlimited growth
    if len(scratchpad['entries']) > 50:
        scratchpad['entries'] = scratchpad['entries'][-50:]
    
    save_scratchpad(scratchpad)
    
    return {
        'success': True,
        'message': 'Entry added to scratchpad',
        'data': scratchpad,
        'entry': entry
    }

async def scratchpad_clear() -> Dict[str, Any]:
    """Clear scratchpad content"""
    scratchpad = load_scratchpad()
    
    cleared_scratchpad = {
        'content': '',
        'entries': [],
        'last_updated': datetime.now().isoformat(),
        'created_at': scratchpad.get('created_at', datetime.now().isoformat())
    }
    
    save_scratchpad(cleared_scratchpad)
    
    return {
        'success': True,
        'message': 'Scratchpad cleared',
        'data': cleared_scratchpad
    }

# MCP tool definitions that can be imported by servers
SCRATCHPAD_TOOLS = [
    {
        'name': 'scratchpad_read',
        'description': 'Read the current scratchpad content',
        'inputSchema': {
            'type': 'object',
            'properties': {}
        },
        'handler': scratchpad_read
    },
    {
        'name': 'scratchpad_write',
        'description': 'Write content to scratchpad (replaces existing content)',
        'inputSchema': {
            'type': 'object',
            'properties': {
                'content': {
                    'type': 'string',
                    'description': 'Content to write to scratchpad'
                }
            },
            'required': ['content']
        },
        'handler': scratchpad_write
    },
    {
        'name': 'scratchpad_append',
        'description': 'Append content to scratchpad',
        'inputSchema': {
            'type': 'object',
            'properties': {
                'content': {
                    'type': 'string',
                    'description': 'Content to append to scratchpad'
                }
            },
            'required': ['content']
        },
        'handler': scratchpad_append
    },
    {
        'name': 'scratchpad_add_entry',
        'description': 'Add a timestamped entry to scratchpad',
        'inputSchema': {
            'type': 'object',
            'properties': {
                'content': {
                    'type': 'string',
                    'description': 'Entry content'
                },
                'author': {
                    'type': 'string',
                    'description': 'Author of the entry (agent name)',
                    'default': 'unknown'
                }
            },
            'required': ['content']
        },
        'handler': scratchpad_add_entry
    },
    {
        'name': 'scratchpad_clear',
        'description': 'Clear all scratchpad content',
        'inputSchema': {
            'type': 'object',
            'properties': {}
        },
        'handler': scratchpad_clear
    }
]