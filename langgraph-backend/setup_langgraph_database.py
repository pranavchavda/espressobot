#!/usr/bin/env python3
"""
Setup script for creating a duplicate database for langgraph-backend system.

This script creates a new database called 'espressobot_langgraph' with the same
schema as the existing 'espressobot_dev' database, but without copying user data.
"""

import asyncio
import asyncpg
import os
import sys
from pathlib import Path

# Database configuration
SOURCE_DB_URL = "postgresql://espressobot:localdev123@localhost:5432/espressobot_dev"
TARGET_DB_URL = "postgresql://espressobot:localdev123@localhost:5432/espressobot_langgraph" 
ADMIN_DB_URL = "postgresql://postgres:@localhost:5432/postgres"  # For creating database

async def create_database():
    """Create the new database if it doesn't exist."""
    print("🏗️  Creating new database 'espressobot_langgraph'...")
    
    try:
        # Connect as admin to create database
        conn = await asyncpg.connect("postgresql://postgres@localhost:5432/postgres")
        
        # Check if database exists
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = 'espressobot_langgraph'"
        )
        
        if exists:
            print("✅ Database 'espressobot_langgraph' already exists")
        else:
            # Create database
            await conn.execute("CREATE DATABASE espressobot_langgraph OWNER espressobot")
            print("✅ Database 'espressobot_langgraph' created successfully")
            
        await conn.close()
        
    except Exception as e:
        print(f"❌ Error creating database: {e}")
        print("💡 You may need to create the database manually with superuser privileges:")
        print("   sudo -u postgres psql -c \"CREATE DATABASE espressobot_langgraph OWNER espressobot;\"")
        return False
    
    return True

async def copy_schema():
    """Copy the schema from source to target database."""
    print("📋 Copying schema from espressobot_dev to espressobot_langgraph...")
    
    try:
        # Read schema from file
        schema_file = Path(__file__).parent / "schema.sql"
        if not schema_file.exists():
            print("❌ schema.sql not found")
            return False
            
        with open(schema_file, 'r') as f:
            schema_sql = f.read()
        
        # Connect to target database
        conn = await asyncpg.connect(TARGET_DB_URL)
        
        # Execute schema
        await conn.execute(schema_sql)
        print("✅ Schema copied successfully")
        
        await conn.close()
        
    except Exception as e:
        print(f"❌ Error copying schema: {e}")
        return False
    
    return True

async def copy_essential_data():
    """Copy essential configuration data (no user data)."""
    print("📦 Copying essential configuration data...")
    
    try:
        # Connect to both databases
        source_conn = await asyncpg.connect(SOURCE_DB_URL)
        target_conn = await asyncpg.connect(TARGET_DB_URL)
        
        # Tables to copy (configuration data only, no user data)
        tables_to_copy = [
            "agents",  # Agent configurations
            "prompt_fragments",  # System prompts
            # Note: Skipping user-specific tables like conversations, memories, etc.
        ]
        
        for table in tables_to_copy:
            try:
                # Check if table exists in source
                exists = await source_conn.fetchval(
                    "SELECT 1 FROM information_schema.tables WHERE table_name = $1", 
                    table
                )
                
                if not exists:
                    print(f"⚠️  Table '{table}' doesn't exist in source database, skipping")
                    continue
                
                # Get data from source
                rows = await source_conn.fetch(f"SELECT * FROM {table}")
                
                if rows:
                    # Insert into target
                    columns = list(rows[0].keys())
                    placeholders = ", ".join([f"${i+1}" for i in range(len(columns))])
                    columns_str = ", ".join(columns)
                    
                    insert_query = f"INSERT INTO {table} ({columns_str}) VALUES ({placeholders})"
                    
                    for row in rows:
                        await target_conn.execute(insert_query, *row.values())
                    
                    print(f"✅ Copied {len(rows)} rows from {table}")
                else:
                    print(f"ℹ️  Table '{table}' is empty, skipping")
                    
            except Exception as e:
                print(f"⚠️  Error copying table '{table}': {e}")
        
        await source_conn.close()
        await target_conn.close()
        
    except Exception as e:
        print(f"❌ Error copying data: {e}")
        return False
    
    return True

async def verify_database():
    """Verify the new database is working correctly."""
    print("🔍 Verifying database setup...")
    
    try:
        conn = await asyncpg.connect(TARGET_DB_URL)
        
        # Check tables exist
        tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        
        print(f"✅ Found {len(tables)} tables:")
        for table in tables:
            print(f"   - {table['table_name']}")
        
        # Check pgvector extension
        vector_ext = await conn.fetchval("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
        if vector_ext:
            print("✅ pgvector extension is installed")
        else:
            print("⚠️  pgvector extension not found")
        
        await conn.close()
        
    except Exception as e:
        print(f"❌ Error verifying database: {e}")
        return False
    
    return True

async def main():
    """Main setup function."""
    print("🚀 Setting up duplicate database for langgraph-backend")
    print("="*50)
    
    # Step 1: Create database
    if not await create_database():
        print("❌ Database creation failed. Please create manually and try again.")
        sys.exit(1)
    
    # Step 2: Copy schema
    if not await copy_schema():
        print("❌ Schema copy failed")
        sys.exit(1)
    
    # Step 3: Copy essential data
    if not await copy_essential_data():
        print("❌ Data copy failed")
        sys.exit(1)
    
    # Step 4: Verify setup
    if not await verify_database():
        print("❌ Database verification failed")
        sys.exit(1)
    
    print("="*50)
    print("✅ Database setup complete!")
    print("💡 To use the new database, copy .env.langgraph to .env:")
    print("   cp .env.langgraph .env")
    print("🚀 Then start the server with: python run.py")

if __name__ == "__main__":
    asyncio.run(main())