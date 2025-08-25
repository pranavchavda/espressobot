#!/usr/bin/env python3
"""
Memory Deduplication Cron Task
Run this script periodically to automatically deduplicate memories

Usage:
  python scripts/memory_deduplication_cron.py [--threshold 0.85] [--dry-run]
"""

import asyncio
import argparse
import logging
import sys
import os
from datetime import datetime
from pathlib import Path

# Add app directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.memory.memory_deduplication import get_deduplication_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('memory_deduplication.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def deduplicate_all_users(threshold: float = 0.85, dry_run: bool = False):
    """
    Deduplicate memories for all users
    """
    service = get_deduplication_service()
    service.similarity_threshold = threshold
    
    logger.info(f"Starting memory deduplication cron job (threshold: {threshold}, dry_run: {dry_run})")
    
    # Get all unique user IDs from memories table
    user_ids = await service.memory_manager.db.fetch("""
        SELECT DISTINCT user_id 
        FROM memories 
        WHERE status = 'active'
        ORDER BY user_id
    """)
    
    total_stats = {
        "users_processed": 0,
        "total_groups_found": 0,
        "total_memories_analyzed": 0,
        "total_memories_merged": 0,
        "total_memories_removed": 0,
        "errors": 0
    }
    
    for row in user_ids:
        user_id = row['user_id']
        
        try:
            logger.info(f"Processing user: {user_id}")
            
            # Run deduplication for this user
            user_stats = await service.deduplicate_memories(
                user_id=user_id,
                dry_run=dry_run
            )
            
            # Accumulate stats
            total_stats["users_processed"] += 1
            total_stats["total_groups_found"] += user_stats["groups_found"]
            total_stats["total_memories_analyzed"] += user_stats["memories_analyzed"]
            total_stats["total_memories_merged"] += user_stats["memories_merged"]
            total_stats["total_memories_removed"] += user_stats["memories_removed"]
            
            if user_stats["groups_found"] > 0:
                logger.info(f"  User {user_id}: Found {user_stats['groups_found']} groups, "
                           f"removed {user_stats['memories_removed']} duplicates")
            else:
                logger.info(f"  User {user_id}: No duplicates found")
                
        except Exception as e:
            logger.error(f"Error processing user {user_id}: {e}")
            total_stats["errors"] += 1
    
    # Log final summary
    logger.info(f"Deduplication cron job completed:")
    logger.info(f"  Users processed: {total_stats['users_processed']}")
    logger.info(f"  Total duplicate groups found: {total_stats['total_groups_found']}")
    logger.info(f"  Total memories analyzed: {total_stats['total_memories_analyzed']}")
    logger.info(f"  Total memories merged: {total_stats['total_memories_merged']}")
    logger.info(f"  Total memories removed: {total_stats['total_memories_removed']}")
    logger.info(f"  Errors: {total_stats['errors']}")
    
    return total_stats

async def deduplicate_user(user_id: str, threshold: float = 0.85, dry_run: bool = False):
    """
    Deduplicate memories for a specific user
    """
    service = get_deduplication_service()
    service.similarity_threshold = threshold
    
    logger.info(f"Starting deduplication for user {user_id} (threshold: {threshold}, dry_run: {dry_run})")
    
    stats = await service.deduplicate_memories(
        user_id=user_id,
        dry_run=dry_run
    )
    
    logger.info(f"Deduplication completed for user {user_id}:")
    logger.info(f"  Groups found: {stats['groups_found']}")
    logger.info(f"  Memories analyzed: {stats['memories_analyzed']}")
    logger.info(f"  Memories merged: {stats['memories_merged']}")
    logger.info(f"  Memories removed: {stats['memories_removed']}")
    
    return stats

def main():
    parser = argparse.ArgumentParser(description="Memory deduplication cron task")
    parser.add_argument("--threshold", type=float, default=0.85,
                       help="Similarity threshold (0.0-1.0, default: 0.85)")
    parser.add_argument("--dry-run", action="store_true",
                       help="Run in dry-run mode (don't make changes)")
    parser.add_argument("--user", type=str,
                       help="Process only a specific user ID")
    
    args = parser.parse_args()
    
    # Validate threshold
    if not (0.0 <= args.threshold <= 1.0):
        logger.error("Threshold must be between 0.0 and 1.0")
        sys.exit(1)
    
    try:
        if args.user:
            # Process single user
            stats = asyncio.run(deduplicate_user(
                user_id=args.user,
                threshold=args.threshold,
                dry_run=args.dry_run
            ))
        else:
            # Process all users
            stats = asyncio.run(deduplicate_all_users(
                threshold=args.threshold,
                dry_run=args.dry_run
            ))
        
        logger.info("Memory deduplication cron job finished successfully")
        
    except Exception as e:
        logger.error(f"Cron job failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()