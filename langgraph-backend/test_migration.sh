#!/bin/bash

# Test script for memory migration
# This script demonstrates how to use the migration script

echo "🧪 Testing Memory Migration Script"
echo "================================="

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please create it first:"
    echo "   python -m venv venv"
    echo "   source venv/bin/activate"
    echo "   pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Check if script exists
if [ ! -f "migrate_memory_to_postgres.py" ]; then
    echo "❌ Migration script not found"
    exit 1
fi

# Test script help
echo "📝 Testing script help..."
python migrate_memory_to_postgres.py --help

echo
echo "📋 Environment Requirements:"
echo "  - DATABASE_URL: Required PostgreSQL connection string"
echo "  - OPENAI_API_KEY: Required for embedding generation"
echo

# Check environment variables
if [ -z "$DATABASE_URL" ]; then
    echo "⚠️  DATABASE_URL not set"
    echo "   Example: export DATABASE_URL='postgresql://user:pass@localhost:5432/dbname'"
else
    echo "✅ DATABASE_URL is set"
fi

if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  OPENAI_API_KEY not set"
    echo "   Please set your OpenAI API key"
else
    echo "✅ OPENAI_API_KEY is set"
fi

echo
echo "🚀 Usage Examples:"
echo "  # Basic migration (preserves existing data):"
echo "  python migrate_memory_to_postgres.py"
echo
echo "  # Force recreate all tables (destroys existing data):"
echo "  python migrate_memory_to_postgres.py --force-recreate"
echo
echo "  # Skip system testing after migration:"
echo "  python migrate_memory_to_postgres.py --skip-test"
echo
echo "  # Force recreate and skip tests:"
echo "  python migrate_memory_to_postgres.py --force-recreate --skip-test"
echo

if [ -n "$DATABASE_URL" ] && [ -n "$OPENAI_API_KEY" ]; then
    echo "🎯 Environment is ready for migration!"
    echo "   Run: python migrate_memory_to_postgres.py"
else
    echo "⚠️  Please set required environment variables before running migration"
fi