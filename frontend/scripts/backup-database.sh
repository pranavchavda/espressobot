#!/bin/bash

# Load environment variables
if [ -f .env ]; then
    export $(grep -E '^DATABASE_URL=' .env | xargs)
fi

# Parse DATABASE_URL
if [ -z "$DATABASE_URL" ]; then
    echo "❌ DATABASE_URL not found in .env file"
    exit 1
fi

# Extract connection details from DATABASE_URL
# Format: postgresql://user:pass@host:port/dbname
DB_USER=$(echo $DATABASE_URL | sed -E 's/postgresql:\/\/([^:]+):.*/\1/')
DB_PASS=$(echo $DATABASE_URL | sed -E 's/postgresql:\/\/[^:]+:([^@]+)@.*/\1/')
DB_HOST=$(echo $DATABASE_URL | sed -E 's/postgresql:\/\/[^@]+@([^:]+):.*/\1/')
DB_PORT=$(echo $DATABASE_URL | sed -E 's/postgresql:\/\/[^@]+@[^:]+:([^\/]+).*/\1/')
DB_NAME=$(echo $DATABASE_URL | sed -E 's/postgresql:\/\/[^\/]+\///')

# Backup configuration
BACKUP_DIR="backups/$(date +%Y-%m-%d)"
TIMESTAMP=$(date +%H%M%S)
BACKUP_FILE="$BACKUP_DIR/espressobot_production_$(date +%Y%m%d)_${TIMESTAMP}.sql"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

echo "🔵 Starting database backup..."
echo "📦 Database: $DB_NAME@$DB_HOST"
echo "📁 Backup location: $BACKUP_FILE"

# Create the backup using pg_dump
PGPASSWORD="$DB_PASS" pg_dump \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    --verbose \
    --no-owner \
    --no-privileges \
    --format=plain \
    --encoding=UTF8 \
    > "$BACKUP_FILE"

# Check if backup was successful
if [ $? -eq 0 ]; then
    # Get file size
    SIZE=$(ls -lh "$BACKUP_FILE" | awk '{print $5}')
    echo "✅ Backup completed successfully!"
    echo "📊 Backup size: $SIZE"
    
    # Compress the backup
    echo "🗜️  Compressing backup..."
    gzip "$BACKUP_FILE"
    
    COMPRESSED_SIZE=$(ls -lh "${BACKUP_FILE}.gz" | awk '{print $5}')
    echo "✅ Compression complete!"
    echo "📊 Compressed size: $COMPRESSED_SIZE"
    echo "📍 Final backup: ${BACKUP_FILE}.gz"
else
    echo "❌ Backup failed!"
    exit 1
fi