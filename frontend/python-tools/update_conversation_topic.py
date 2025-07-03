#!/usr/bin/env python3
"""
Update conversation topic tool for bash agents
"""

import os
import sys
import argparse
import sqlite3
from datetime import datetime

def update_conversation_topic(conversation_id, topic_title, topic_details=None):
    """Update the topic for a conversation"""
    
    # Database path
    db_path = os.path.join(os.path.dirname(__file__), '..', 'prisma', 'dev.db')
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Update the conversation
        if topic_details:
            cursor.execute('''
                UPDATE conversations 
                SET topic_title = ?, topic_details = ?, updated_at = ?
                WHERE id = ?
            ''', (topic_title, topic_details, datetime.now().isoformat(), conversation_id))
        else:
            cursor.execute('''
                UPDATE conversations 
                SET topic_title = ?, updated_at = ?
                WHERE id = ?
            ''', (topic_title, datetime.now().isoformat(), conversation_id))
        
        # Check if update was successful
        if cursor.rowcount == 0:
            print(f"Error: Conversation {conversation_id} not found")
            return False
        
        conn.commit()
        conn.close()
        
        print(f"Successfully updated topic for conversation {conversation_id}")
        print(f"Topic: {topic_title}")
        if topic_details:
            print(f"Details: {topic_details}")
        
        return True
        
    except Exception as e:
        print(f"Error updating conversation topic: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Update conversation topic')
    parser.add_argument('conversation_id', type=int, help='Conversation ID')
    parser.add_argument('topic_title', help='Concise topic title (max 200 chars)')
    parser.add_argument('--details', help='Optional detailed description of the topic')
    
    args = parser.parse_args()
    
    # Get conversation ID from environment if not provided and argument is 0
    if args.conversation_id == 0:
        conv_id = os.environ.get('ESPRESSOBOT_CONVERSATION_ID')
        if conv_id:
            args.conversation_id = int(conv_id)
        else:
            print("Error: No conversation ID provided and ESPRESSOBOT_CONVERSATION_ID not set")
            sys.exit(1)
    
    # Truncate title if too long
    topic_title = args.topic_title[:200]
    
    success = update_conversation_topic(
        args.conversation_id,
        topic_title,
        args.details
    )
    
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()