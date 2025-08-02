# 🚨 CRITICAL: Shopify Sync Deletes Manual Matches

## Issue Discovered

The current Shopify sync process **DELETES ALL MANUAL MATCHES** when syncing products. This happens because:

1. The sync deletes all IDC products for a brand: `prisma.idc_products.deleteMany({ where: { vendor: brandName } })`
2. The schema has CASCADE delete: `onDelete: Cascade`
3. This cascades to delete ALL product_matches (including manual ones!)

## Impact

- **All 80+ manual matches created today are at risk**
- Every time a sync runs, manual matches for that brand are permanently deleted
- No way to recover without database backups

## Immediate Actions Required

### 1. STOP Using Unsafe Sync
```bash
# DO NOT USE:
POST /api/price-monitor/shopify-sync/sync-idc-products

# This endpoint deletes all products and their matches!
```

### 2. Use Safe Sync Instead
```bash
# USE THIS:
POST /api/price-monitor/shopify-sync-safe/sync-idc-products-safe

# This endpoint:
# - Updates existing products instead of deleting
# - Marks missing products as unavailable
# - Preserves ALL manual matches
```

### 3. Check Your Manual Matches
```bash
node scripts/check-manual-matches-status.js
```

### 4. Backup Manual Matches Immediately
```sql
-- Export all manual matches
SELECT * FROM product_matches 
WHERE is_manual_match = true 
INTO OUTFILE 'manual_matches_backup.csv';
```

## How the Safe Sync Works

Instead of delete-and-recreate, the safe sync:

1. **Tracks seen products** during sync
2. **Updates existing products** with new data
3. **Creates new products** only if they don't exist
4. **Marks unseen products as unavailable** (instead of deleting)
5. **Preserves all relationships** and manual matches

## Code Changes Made

### 1. Created `/server/api/price-monitor/shopify-sync-safe.js`
- New safe sync endpoint that preserves matches
- Updates instead of deletes
- Tracks manual match preservation

### 2. Added to router at `/server/api/price-monitor/index.js`
- New route: `/shopify-sync-safe`

### 3. Created status check script
- `/scripts/check-manual-matches-status.js`
- Shows all manual matches and their status

## Recovery Options

If manual matches were already deleted:

1. **From database backup** (if available):
   ```bash
   # Restore from today's backup
   psql -h node.idrinkcoffee.info -U espressobot -d espressobot_production < backup.sql
   ```

2. **From CSV export** (if you exported earlier):
   ```bash
   # Re-import matches from CSV
   node scripts/add-manual-matches.js
   ```

3. **Recreate manually** using the match analyzer

## Prevention Going Forward

1. **Always use safe sync endpoint**
2. **Regular backups of manual matches**
3. **Consider removing CASCADE delete** from schema
4. **Add manual match protection** to all sync operations

## Technical Details

The problem is in the Prisma schema:
```prisma
model product_matches {
  // ...
  idc_products idc_products @relation(fields: [idc_product_id], references: [id], onDelete: Cascade)
  //                                                                            ^^^^^^^^^^^^^^^^
  // This CASCADE delete is the problem!
}
```

When an idc_product is deleted, it cascades to delete all matches.

## Long-term Fix Options

1. **Change schema to SET NULL**:
   ```prisma
   onDelete: SetNull  // Instead of Cascade
   ```

2. **Add soft delete**:
   - Add `deleted_at` field
   - Never actually delete products
   - Filter by deleted_at in queries

3. **Separate manual matches table**:
   - Create `manual_product_matches` table
   - No cascade delete relationship
   - Merge results in queries

---

**Created**: August 2, 2025  
**Severity**: CRITICAL  
**Status**: Mitigated with safe sync endpoint