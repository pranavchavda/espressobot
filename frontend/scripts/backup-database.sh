#!/bin/bash

# Database connection details from .env
DB_HOST="node.idrinkcoffee.info"
DB_PORT="5432"
DB_NAME="espressobot_production"
DB_USER="espressobot"
DB_PASS="csEZWEzFk55D"

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