import express from 'express';
import { db } from '../../config/database.js';
import { nanoid } from 'nanoid';

const prisma = db;
const router = express.Router();

// Record a violation in history
export async function recordViolation({
  productMatchId,
  violationType,
  competitorPrice,
  idcPrice,
  violationAmount,
  violationPercent,
  previousPrice = null,
  screenshotUrl = null,
  competitorUrl = null,
  notes = null
}) {
  try {
    const violationRecord = await prisma.violation_history.create({
      data: {
        id: nanoid(),
        product_match_id: productMatchId,
        violation_type: violationType,
        competitor_price: competitorPrice,
        idc_price: idcPrice,
        violation_amount: violationAmount,
        violation_percent: violationPercent,
        previous_price: previousPrice,
        price_change: previousPrice ? competitorPrice - previousPrice : null,
        screenshot_url: screenshotUrl,
        competitor_url: competitorUrl,
        notes: notes,
        detected_at: new Date(),
        updated_at: new Date()
      }
    });

    // Update product_match with violation tracking
    await prisma.product_matches.update({
      where: { id: productMatchId },
      data: {
        is_map_violation: true,
        violation_amount: violationAmount,
        violation_percentage: violationPercent,
        first_violation_date: await getFirstViolationDate(productMatchId),
        last_checked_at: new Date()
      }
    });

    return violationRecord;
  } catch (error) {
    console.error('Error recording violation:', error);
    throw error;
  }
}

// Get first violation date for a product match
async function getFirstViolationDate(productMatchId) {
  const firstViolation = await prisma.violation_history.findFirst({
    where: { product_match_id: productMatchId },
    orderBy: { detected_at: 'asc' },
    select: { detected_at: true }
  });
  
  return firstViolation?.detected_at || new Date();
}

// Enhanced MAP violation scanner that records history
router.post('/scan-and-record', async (req, res) => {
  try {
    const { 
      brands, 
      severity_filter,
      record_history = true,
      capture_screenshots = false,
      dry_run = false 
    } = req.body;

    console.log('🔍 Starting MAP violation scan with history recording...');
    
    const results = {
      total_matches_scanned: 0,
      violations_found: 0,
      history_recorded: 0,
      by_severity: {
        minor: 0,
        moderate: 0,
        severe: 0
      },
      violations: []
    };

    // Get product matches to scan
    const whereClause = {};
    if (brands) {
      whereClause.idc_products = { vendor: { in: brands } };
    }

    const productMatches = await prisma.product_matches.findMany({
      where: whereClause,
      include: {
        idc_products: true,
        competitor_products: {
          include: {
            competitors: true
          }
        },
        violation_history: {
          orderBy: { detected_at: 'desc' },
          take: 1
        }
      }
    });

    console.log(`📦 Scanning ${productMatches.length} product matches for violations`);

    for (const match of productMatches) {
      const { idc_products, competitor_products, violation_history } = match;
      
      const mapPrice = parseFloat(idc_products.price);
      const competitorPrice = parseFloat(competitor_products.price);
      const lastViolation = violation_history[0];

      if (!mapPrice || !competitorPrice || competitorPrice >= mapPrice) {
        // No violation or invalid prices
        if (match.is_map_violation && competitorPrice >= mapPrice) {
          // Violation resolved - update the match
          if (!dry_run) {
            await prisma.product_matches.update({
              where: { id: match.id },
              data: {
                is_map_violation: false,
                violation_amount: null,
                violation_percentage: null,
                last_checked_at: new Date()
              }
            });
          }
        }
        continue;
      }

      const violationAmount = mapPrice - competitorPrice;
      const violationPercent = (violationAmount / mapPrice) * 100;
      
      // Determine severity
      let severity = null;
      if (violationPercent >= 20) severity = 'severe';
      else if (violationPercent >= 10) severity = 'moderate';
      else if (violationPercent >= 1) severity = 'minor';
      
      if (severity && (!severity_filter || severity === severity_filter)) {
        // Check if this is a new violation or price change
        const isNewViolation = !lastViolation;
        const isPriceChange = lastViolation && 
          parseFloat(lastViolation.competitor_price) !== competitorPrice;

        if ((isNewViolation || isPriceChange) && record_history && !dry_run) {
          // Record in violation history
          await recordViolation({
            productMatchId: match.id,
            violationType: `map_violation_${severity}`,
            competitorPrice: competitorPrice,
            idcPrice: mapPrice,
            violationAmount: violationAmount,
            violationPercent: violationPercent,
            previousPrice: lastViolation?.competitor_price || null,
            competitorUrl: competitor_products.product_url,
            notes: isNewViolation ? 'Initial violation detected' : 'Price changed'
          });
          
          results.history_recorded++;
        }

        results.violations_found++;
        results.by_severity[severity]++;
        
        results.violations.push({
          match_id: match.id,
          is_new: isNewViolation,
          price_changed: isPriceChange,
          idc_product: {
            title: idc_products.title,
            vendor: idc_products.vendor,
            sku: idc_products.sku,
            price: mapPrice
          },
          competitor_product: {
            title: competitor_products.title,
            vendor: competitor_products.vendor,
            sku: competitor_products.sku,
            price: competitorPrice,
            competitor: competitor_products.competitors.name,
            domain: competitor_products.competitors.domain,
            url: competitor_products.product_url
          },
          violation: {
            severity: severity,
            amount: violationAmount,
            percentage: violationPercent.toFixed(2),
            previous_price: lastViolation?.competitor_price || null,
            first_detected: match.first_violation_date || new Date(),
            last_detected: new Date()
          }
        });
      }

      results.total_matches_scanned++;
    }

    console.log(`✅ Scan completed: ${results.violations_found} violations found, ${results.history_recorded} recorded`);

    res.json({
      message: `MAP violation scan completed${dry_run ? ' (dry run)' : ''}`,
      ...results
    });

  } catch (error) {
    console.error('Error scanning violations:', error);
    res.status(500).json({ error: 'Failed to scan violations' });
  }
});

// Get violation history for a product
router.get('/history/:productMatchId', async (req, res) => {
  try {
    const { productMatchId } = req.params;
    const { 
      limit = 100,
      offset = 0,
      start_date,
      end_date
    } = req.query;

    const where = { product_match_id: productMatchId };
    
    if (start_date || end_date) {
      where.detected_at = {};
      if (start_date) where.detected_at.gte = new Date(start_date);
      if (end_date) where.detected_at.lte = new Date(end_date);
    }

    const [history, total] = await Promise.all([
      prisma.violation_history.findMany({
        where,
        orderBy: { detected_at: 'desc' },
        take: parseInt(limit),
        skip: parseInt(offset),
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
      }),
      prisma.violation_history.count({ where })
    ]);

    res.json({
      history,
      pagination: {
        total,
        limit: parseInt(limit),
        offset: parseInt(offset),
        has_more: offset + limit < total
      }
    });

  } catch (error) {
    console.error('Error fetching violation history:', error);
    res.status(500).json({ error: 'Failed to fetch violation history' });
  }
});

// Get aggregated violation statistics
router.get('/statistics', async (req, res) => {
  try {
    const { 
      brand,
      competitor,
      start_date,
      end_date,
      group_by = 'day' // day, week, month
    } = req.query;

    let where = {};
    
    if (start_date || end_date) {
      where.detected_at = {};
      if (start_date) where.detected_at.gte = new Date(start_date);
      if (end_date) where.detected_at.lte = new Date(end_date);
    }

    if (brand || competitor) {
      where.product_matches = {};
      if (brand) {
        where.product_matches.idc_products = { vendor: brand };
      }
      if (competitor) {
        where.product_matches.competitor_products = {
          competitors: { name: competitor }
        };
      }
    }

    // Get summary statistics
    const [
      totalViolations,
      averageViolation,
      maxViolation,
      activeViolations,
      violationsByType
    ] = await Promise.all([
      // Total violations
      prisma.violation_history.count({ where }),
      
      // Average violation
      prisma.violation_history.aggregate({
        where,
        _avg: {
          violation_percent: true,
          violation_amount: true
        }
      }),
      
      // Max violation
      prisma.violation_history.aggregate({
        where,
        _max: {
          violation_percent: true,
          violation_amount: true
        }
      }),
      
      // Currently active violations
      prisma.product_matches.count({
        where: { is_map_violation: true }
      }),
      
      // Violations by type
      prisma.violation_history.groupBy({
        by: ['violation_type'],
        where,
        _count: { id: true },
        _sum: { violation_amount: true },
        _avg: { violation_percent: true }
      })
    ]);

    // Get all violations for the time period
    const violations = await prisma.violation_history.findMany({
      where,
      orderBy: { detected_at: 'desc' },
      select: {
        detected_at: true,
        violation_percent: true,
        violation_amount: true,
        product_match_id: true
      }
    });

    // Group violations by time period in JavaScript
    const timeSeriesMap = new Map();
    
    violations.forEach(violation => {
      const date = new Date(violation.detected_at);
      let periodKey;
      
      switch (group_by) {
        case 'month':
          periodKey = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
          break;
        case 'week':
          // Get week start date (Sunday)
          const weekStart = new Date(date);
          weekStart.setDate(date.getDate() - date.getDay());
          periodKey = weekStart.toISOString().split('T')[0];
          break;
        default: // day
          periodKey = date.toISOString().split('T')[0];
      }
      
      if (!timeSeriesMap.has(periodKey)) {
        timeSeriesMap.set(periodKey, {
          period: periodKey,
          violations: [],
          uniqueProducts: new Set()
        });
      }
      
      const periodData = timeSeriesMap.get(periodKey);
      periodData.violations.push(violation);
      periodData.uniqueProducts.add(violation.product_match_id);
    });

    // Calculate aggregates for each period
    const timeSeries = Array.from(timeSeriesMap.entries())
      .map(([period, data]) => ({
        period: new Date(period + (group_by === 'month' ? '-01' : '')),
        violation_count: data.violations.length,
        avg_violation_pct: data.violations.reduce((sum, v) => sum + v.violation_percent, 0) / data.violations.length,
        total_impact: data.violations.reduce((sum, v) => sum + (v.violation_amount || 0), 0),
        unique_products: data.uniqueProducts.size
      }))
      .sort((a, b) => b.period - a.period);

    res.json({
      summary: {
        total_violations: totalViolations,
        active_violations: activeViolations,
        average_violation_percent: averageViolation._avg.violation_percent ? parseFloat(averageViolation._avg.violation_percent) : 0,
        average_violation_amount: averageViolation._avg.violation_amount ? parseFloat(averageViolation._avg.violation_amount) : 0,
        max_violation_percent: maxViolation._max.violation_percent ? parseFloat(maxViolation._max.violation_percent) : 0,
        max_violation_amount: maxViolation._max.violation_amount ? parseFloat(maxViolation._max.violation_amount) : 0
      },
      by_type: violationsByType.map(type => ({
        ...type,
        _avg: {
          violation_percent: type._avg.violation_percent ? parseFloat(type._avg.violation_percent) : 0
        },
        _sum: {
          violation_amount: type._sum.violation_amount ? parseFloat(type._sum.violation_amount) : 0
        }
      })),
      time_series: timeSeries,
      filters: {
        brand,
        competitor,
        start_date,
        end_date,
        group_by
      }
    });

  } catch (error) {
    console.error('Error fetching violation statistics:', error);
    res.status(500).json({ error: 'Failed to fetch violation statistics' });
  }
});

// Get violation history report (CSV export)
router.get('/export', async (req, res) => {
  try {
    const { 
      brand,
      competitor,
      start_date,
      end_date,
      format = 'csv'
    } = req.query;

    let where = {};
    
    if (start_date || end_date) {
      where.detected_at = {};
      if (start_date) where.detected_at.gte = new Date(start_date);
      if (end_date) where.detected_at.lte = new Date(end_date);
    }

    if (brand || competitor) {
      where.product_matches = {};
      if (brand) {
        where.product_matches.idc_products = { vendor: brand };
      }
      if (competitor) {
        where.product_matches.competitor_products = {
          competitors: { name: competitor }
        };
      }
    }

    const violations = await prisma.violation_history.findMany({
      where,
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
      },
      orderBy: { detected_at: 'desc' }
    });

    if (format === 'csv') {
      const csv = [
        'Date,Brand,Product,SKU,MAP Price,Competitor,Competitor Price,Violation Amount,Violation %,Type,Notes',
        ...violations.map(v => {
          const match = v.product_matches;
          return [
            v.detected_at.toISOString(),
            match.idc_products.vendor,
            `"${match.idc_products.title}"`,
            match.idc_products.sku || '',
            v.idc_price,
            match.competitor_products.competitors.name,
            v.competitor_price,
            v.violation_amount,
            v.violation_percent.toFixed(2),
            v.violation_type,
            `"${v.notes || ''}"`
          ].join(',');
        })
      ].join('\n');

      res.setHeader('Content-Type', 'text/csv');
      res.setHeader('Content-Disposition', `attachment; filename="violation-history-${new Date().toISOString().split('T')[0]}.csv"`);
      res.send(csv);
    } else {
      res.json(violations);
    }

  } catch (error) {
    console.error('Error exporting violation history:', error);
    res.status(500).json({ error: 'Failed to export violation history' });
  }
});

export default router;