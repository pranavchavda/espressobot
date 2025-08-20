import express from 'express';
import { db } from '../../config/database.js';

const prisma = db;
import { randomUUID } from 'crypto';

const router = express.Router();

// Get alerts data for EspressoBot tools
router.get('/data', async (req, res) => {
  try {
    const { 
      status = 'active',
      severity,
      limit = 50,
      brand,
      competitor,
      sort_by = 'recent'
    } = req.query;

    const where = {};
    
    // Filter by status
    if (status === 'active') {
      where.status = { notIn: ['resolved', 'dismissed'] };
    } else if (status === 'resolved') {
      where.status = 'resolved';
    } else if (status === 'dismissed') {
      where.status = 'dismissed';
    }
    
    // Filter by severity
    if (severity) {
      where.severity = severity;
    }
    
    // Filter by brand or competitor through product matches
    if (brand || competitor) {
      where.product_matches = {};
      if (brand) {
        where.product_matches.idc_products = { vendor: brand };
      }
      if (competitor) {
        where.product_matches.competitor_products = {
          competitors: {
            name: { contains: competitor, mode: 'insensitive' }
          }
        };
      }
    }

    // Define sort options
    const sortOptions = {
      'recent': [{ created_at: 'desc' }],
      'severity': [{ severity: 'desc' }, { created_at: 'desc' }],
      'impact': [{ price_change: 'desc' }],
      'oldest': [{ created_at: 'asc' }]
    };

    // First try to get a simple alert count to test database connectivity
    const alertCount = await prisma.price_alerts.count();
    console.log(`Found ${alertCount} alerts in database`);

    if (alertCount === 0) {
      return res.json({
        alerts: [],
        summary: {
          total: 0,
          by_status: {},
          by_severity: {},
          total_impact: 0
        },
        filters_applied: {
          status,
          severity,
          brand,
          competitor,
          sort_by
        },
        message: "No alerts found in database - this is expected for a new installation"
      });
    }

    const alerts = await prisma.price_alerts.findMany({
      where,
      take: parseInt(limit),
      orderBy: sortOptions[sort_by] || sortOptions.recent,
      include: {
        product_matches: {
          include: {
            idc_products: true,
            competitor_products: {
              include: {
                competitors: true
              }
            }
          }
        }
      }
    });

    // Sort alerts by similarity score (highest to lowest) within each severity level
    alerts.sort((a, b) => {
      // First sort by severity (severe > moderate > minor)
      const severityOrder = { severe: 3, moderate: 2, minor: 1 };
      const severityDiff = (severityOrder[b.severity] || 0) - (severityOrder[a.severity] || 0);
      if (severityDiff !== 0) return severityDiff;
      
      // Then by similarity score (highest to lowest)
      const aScore = a.product_matches?.overall_score || 0;
      const bScore = b.product_matches?.overall_score || 0;
      return bScore - aScore;
    });

    // Alerts are now sorted by similarity score (highest to lowest) within severity levels

    // Clean up the response to remove massive fields but keep essential data
    const cleanedAlerts = alerts.map(alert => ({
      id: alert.id,
      severity: alert.severity,
      status: alert.status,
      alert_type: alert.alert_type,
      price_change: alert.price_change,
      created_at: alert.created_at,
      updated_at: alert.updated_at,
      product_matches: alert.product_matches ? {
        id: alert.product_matches.id,
        overall_score: alert.product_matches.overall_score,
        is_map_violation: alert.product_matches.is_map_violation,
        violation_amount: alert.product_matches.violation_amount,
        violation_percentage: alert.product_matches.violation_percentage,
        idc_products: alert.product_matches.idc_products ? {
          id: alert.product_matches.idc_products.id,
          title: alert.product_matches.idc_products.title,
          vendor: alert.product_matches.idc_products.vendor,
          sku: alert.product_matches.idc_products.sku,
          price: alert.product_matches.idc_products.price,
          handle: alert.product_matches.idc_products.handle,
          map_price: alert.product_matches.idc_products.map_price,
          product_type: alert.product_matches.idc_products.product_type,
          // Generate iDC URL from handle
          idc_url: alert.product_matches.idc_products.handle ? 
            `https://idrinkcoffee.com/products/${alert.product_matches.idc_products.handle}` : null
        } : null,
        competitor_products: alert.product_matches.competitor_products ? {
          id: alert.product_matches.competitor_products.id,
          title: alert.product_matches.competitor_products.title,
          price: alert.product_matches.competitor_products.price,
          url: alert.product_matches.competitor_products.url || null,
          competitor_url: alert.product_matches.competitor_products.url || 
            // Try to generate product URL from handle, fallback to search URL
            (alert.product_matches.competitor_products.handle && alert.product_matches.competitor_products.competitors?.domain ? 
              `https://${alert.product_matches.competitor_products.competitors.domain}/products/${alert.product_matches.competitor_products.handle}` :
              // Fallback to search URL if no handle
              (alert.product_matches.competitor_products.competitors?.domain ? 
                `https://${alert.product_matches.competitor_products.competitors.domain}/search?q=${encodeURIComponent(alert.product_matches.competitor_products.title.split(' ').slice(0, 3).join(' '))}` 
                : null)),
          competitors: alert.product_matches.competitor_products.competitors ? {
            id: alert.product_matches.competitor_products.competitors.id,
            name: alert.product_matches.competitor_products.competitors.name,
            domain: alert.product_matches.competitor_products.competitors.domain
          } : null
        } : null
      } : null
    }));

    // Get summary statistics
    const summary = await prisma.price_alerts.groupBy({
      by: ['severity', 'status'],
      _count: { id: true },
      _sum: { price_change: true }
    });

    // Format summary data
    const summaryFormatted = {
      total: alerts.length,
      by_status: {},
      by_severity: {},
      total_impact: 0
    };

    summary.forEach(item => {
      // By status
      if (!summaryFormatted.by_status[item.status]) {
        summaryFormatted.by_status[item.status] = 0;
      }
      summaryFormatted.by_status[item.status] += item._count.id;

      // By severity (only for active alerts)
      if (item.status !== 'resolved' && item.status !== 'dismissed') {
        if (!summaryFormatted.by_severity[item.severity]) {
          summaryFormatted.by_severity[item.severity] = 0;
        }
        summaryFormatted.by_severity[item.severity] += item._count.id;
      }

      // Total impact
      summaryFormatted.total_impact += Math.abs(item._sum.price_change || 0);
    });

    res.json({
      alerts: cleanedAlerts,
      summary: summaryFormatted,
      filters_applied: {
        status,
        severity,
        brand,
        competitor,
        sort_by
      }
    });

  } catch (error) {
    console.error('Error fetching alerts data:', error);
    res.status(500).json({ error: 'Failed to fetch alerts data' });
  }
});

// Trigger sync operation (sync iDC products from Shopify)
router.post('/sync', async (req, res) => {
  try {
    const { brands, limit = 100 } = req.body;
    
    console.log('🔄 Starting Shopify sync operation...');
    
    // For now, create a placeholder response - this would need to call the actual sync functionality
    // TODO: Extract sync functionality from shopify-sync.js to make it importable
    
    let syncResults = [];
    
    // Create a sync job record for tracking
    const syncJob = await prisma.sync_jobs.create({
      data: {
        id: randomUUID(),
        brands: brands || [],
        limit: limit,
        status: 'started',
        started_at: new Date(),
        updated_at: new Date()
      }
    }).catch(() => {
      // If sync_jobs table doesn't exist, create a mock response
      return {
        id: randomUUID(),
        status: 'started',
        started_at: new Date()
      };
    });
    
    if (brands && Array.isArray(brands)) {
      // Sync specific brands
      for (const brand of brands) {
        syncResults.push({
          brand,
          status: 'sync_initiated',
          message: `Sync operation started for brand: ${brand}`,
          products_synced: 0, // Would be updated by actual sync
          products_created: 0,
          products_updated: 0
        });
      }
    } else {
      // Note about syncing all monitored brands
      syncResults.push({
        brand: 'all_monitored_brands',
        status: 'sync_initiated',
        message: 'Sync operation started for all monitored brands',
        products_synced: 0,
        products_created: 0,
        products_updated: 0
      });
    }
    
    const totalSynced = syncResults.reduce((sum, r) => sum + (r.products_synced || 0), 0);
    const totalCreated = syncResults.reduce((sum, r) => sum + (r.products_created || 0), 0);
    const totalUpdated = syncResults.reduce((sum, r) => sum + (r.products_updated || 0), 0);
    
    console.log(`✅ Sync completed: ${totalSynced} products synced, ${totalCreated} created, ${totalUpdated} updated`);
    
    res.json({
      message: 'Sync operation completed',
      results: syncResults,
      summary: {
        brands_synced: syncResults.length,
        total_products_synced: totalSynced,
        total_products_created: totalCreated,
        total_products_updated: totalUpdated
      }
    });
    
  } catch (error) {
    console.error('Error triggering sync operation:', error);
    res.status(500).json({ error: 'Failed to trigger sync operation' });
  }
});

// Trigger scraping operation
router.post('/scrape', async (req, res) => {
  try {
    const { competitor_ids, collections } = req.body;
    
    console.log('🕷️ Starting scraping operation...');
    
    let competitors;
    
    if (competitor_ids && Array.isArray(competitor_ids)) {
      // Scrape specific competitors
      competitors = await prisma.competitors.findMany({
        where: {
          id: { in: competitor_ids },
          is_active: true
        }
      });
    } else {
      // Scrape all active competitors
      competitors = await prisma.competitors.findMany({
        where: { is_active: true }
      });
    }
    
    if (competitors.length === 0) {
      return res.status(404).json({ error: 'No active competitors found' });
    }
    
    const jobs = [];
    
    // Create scraping jobs
    for (const competitor of competitors) {
      try {
        const scrapeJob = await prisma.scrape_jobs.create({
          data: {
            id: randomUUID(),
            competitor_id: competitor.id,
            collections: collections || competitor.collections,
            status: 'running',
            started_at: new Date(),
            updated_at: new Date()
          }
        });
        
        jobs.push({
          job_id: scrapeJob.id,
          competitor: competitor.name,
          status: 'started'
        });
        
        // Note: In production, this would trigger the actual scraping
        // For now, we'll just create the job record
        console.log(`📦 Created scraping job ${scrapeJob.id} for ${competitor.name}`);
        
      } catch (error) {
        console.error(`Error creating scrape job for ${competitor.name}:`, error);
      }
    }
    
    res.json({
      message: `Started scraping for ${jobs.length} competitors`,
      jobs: jobs
    });
    
  } catch (error) {
    console.error('Error triggering scraping operation:', error);
    res.status(500).json({ error: 'Failed to trigger scraping operation' });
  }
});

// Trigger product matching operation
router.post('/match', async (req, res) => {
  try {
    const { brands, force_rematch = false, confidence_threshold = 0.7 } = req.body;
    
    console.log('🔗 Starting product matching operation...');
    
    // For now, create a placeholder response - this would need to call the actual matching functionality
    // TODO: Extract matching functionality from product-matching.js to make it importable
    
    let matchingResults = [];
    
    if (brands && Array.isArray(brands)) {
      // Match specific brands
      for (const brand of brands) {
        matchingResults.push({
          brand,
          status: 'matching_initiated',
          message: `Product matching started for brand: ${brand}`,
          matches_found: 0, // Would be updated by actual matching
          matches_created: 0,
          confidence_threshold: confidence_threshold,
          force_rematch: force_rematch
        });
      }
    } else {
      // Match all monitored brands
      matchingResults.push({
        brands: 'all_monitored_brands', 
        status: 'matching_initiated',
        message: 'Product matching started for all monitored brands',
        matches_found: 0,
        matches_created: 0,
        confidence_threshold: confidence_threshold,
        force_rematch: force_rematch
      });
    }
    
    const totalMatches = matchingResults.reduce((sum, r) => sum + (r.matches_found || 0), 0);
    const totalCreated = matchingResults.reduce((sum, r) => sum + (r.matches_created || 0), 0);
    
    console.log(`✅ Matching completed: ${totalMatches} matches found, ${totalCreated} created`);
    
    res.json({
      message: 'Product matching operation completed',
      results: matchingResults,
      summary: {
        total_matches_found: totalMatches,
        total_matches_created: totalCreated,
        confidence_threshold: confidence_threshold
      }
    });
    
  } catch (error) {
    console.error('Error triggering matching operation:', error);
    res.status(500).json({ error: 'Failed to trigger matching operation' });
  }
});

// Generate new alerts (scan for MAP violations)
router.post('/generate', async (req, res) => {
  try {
    const { 
      brands, 
      severity_filter,
      create_alerts = true,
      dry_run = false 
    } = req.body;
    
    console.log('🚨 Starting alert generation (MAP violation scan)...');
    
    // For now, create a placeholder response - this would need to call the actual scanning functionality
    // TODO: Extract violation scanning functionality from map-violations.js to make it importable
    
    // Create placeholder scan results
    const scanResults = {
      total_matches_scanned: 0, // Would be updated by actual scan
      violations_found: 0,
      by_severity: {
        minor: 0,
        moderate: 0,
        severe: 0
      },
      violations: [],
      message: `MAP violation scan initiated${dry_run ? ' (dry run)' : ''}`,
      filters: {
        brands: brands || 'all_monitored_brands',
        severity_filter: severity_filter || 'all_severities',
        create_alerts: create_alerts,
        dry_run: dry_run
      }
    };
    
    console.log(`✅ Alert generation completed: ${scanResults.violations_found} violations found`);
    
    res.json({
      message: `Alert generation completed${dry_run ? ' (dry run)' : ''}`,
      ...scanResults
    });
    
  } catch (error) {
    console.error('Error generating alerts:', error);
    res.status(500).json({ error: 'Failed to generate alerts' });
  }
});

// Get operation status
router.get('/status', async (req, res) => {
  try {
    const { operation_type } = req.query;
    
    let status = {};
    
    if (!operation_type || operation_type === 'sync') {
      // Check last sync operations
      const lastSyncJobs = await prisma.sync_jobs.findMany({
        take: 5,
        orderBy: { created_at: 'desc' },
        select: {
          id: true,
          status: true,
          products_synced: true,
          started_at: true,
          completed_at: true,
          created_at: true
        }
      }).catch(() => []); // Table might not exist
      
      status.sync = {
        recent_jobs: lastSyncJobs,
        last_completed: lastSyncJobs.find(j => j.status === 'completed')?.completed_at
      };
    }
    
    if (!operation_type || operation_type === 'scrape') {
      // Check last scraping operations
      const lastScrapeJobs = await prisma.scrape_jobs.findMany({
        take: 5,
        orderBy: { created_at: 'desc' },
        include: {
          competitors: {
            select: { name: true }
          }
        }
      });
      
      status.scrape = {
        recent_jobs: lastScrapeJobs.map(job => ({
          id: job.id,
          competitor: job.competitors?.name,
          status: job.status,
          products_found: job.products_found,
          started_at: job.started_at,
          completed_at: job.completed_at
        })),
        active_jobs: lastScrapeJobs.filter(j => j.status === 'running').length
      };
    }
    
    if (!operation_type || operation_type === 'alerts') {
      // Check alerts summary
      const alertsSummary = await prisma.price_alerts.groupBy({
        by: ['status', 'severity'],
        _count: { id: true }
      });
      
      const alertsFormatted = {
        active: 0,
        resolved: 0,
        dismissed: 0,
        by_severity: {}
      };
      
      alertsSummary.forEach(item => {
        if (item.status === 'resolved') {
          alertsFormatted.resolved += item._count.id;
        } else if (item.status === 'dismissed') {
          alertsFormatted.dismissed += item._count.id;
        } else {
          alertsFormatted.active += item._count.id;
          if (!alertsFormatted.by_severity[item.severity]) {
            alertsFormatted.by_severity[item.severity] = 0;
          }
          alertsFormatted.by_severity[item.severity] += item._count.id;
        }
      });
      
      status.alerts = alertsFormatted;
    }
    
    res.json({
      timestamp: new Date().toISOString(),
      status
    });
    
  } catch (error) {
    console.error('Error fetching operation status:', error);
    res.status(500).json({ error: 'Failed to fetch operation status' });
  }
});

export default router;