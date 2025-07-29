import express from 'express';
import prisma from '../../lib/prisma.js';

const router = express.Router();

// MAP violation detection engine
class MAPViolationDetector {
  constructor() {
    this.violationThresholds = {
      minor: 0.05,      // 5% below MAP
      moderate: 0.10,   // 10% below MAP  
      severe: 0.20      // 20% below MAP
    };
  }

  // Calculate violation severity
  calculateViolationSeverity(mapPrice, competitorPrice) {
    if (!mapPrice || !competitorPrice || mapPrice <= 0 || competitorPrice <= 0) {
      return null;
    }

    const priceDifference = mapPrice - competitorPrice;
    const violationPercentage = priceDifference / mapPrice;

    if (violationPercentage <= 0) {
      return null; // No violation - competitor price is at or above MAP
    }

    if (violationPercentage >= this.violationThresholds.severe) {
      return 'severe';
    } else if (violationPercentage >= this.violationThresholds.moderate) {
      return 'moderate';
    } else if (violationPercentage >= this.violationThresholds.minor) {
      return 'minor';
    }

    return null; // Below minor threshold
  }

  // Calculate financial impact
  calculateFinancialImpact(mapPrice, competitorPrice, estimatedVolume = 10) {
    const priceDifference = mapPrice - competitorPrice;
    return {
      price_gap: priceDifference,
      percentage_below: (priceDifference / mapPrice) * 100,
      potential_lost_revenue: priceDifference * estimatedVolume,
      competitor_advantage: competitorPrice / mapPrice
    };
  }
}

// Scan for MAP violations
router.post('/scan-violations', async (req, res) => {
  try {
    const { 
      brands, 
      severity_filter,
      create_alerts = true,
      dry_run = false 
    } = req.body;

    console.log('🔍 Starting MAP violation scan...');
    
    const detector = new MAPViolationDetector();
    const results = {
      total_matches_scanned: 0,
      violations_found: 0,
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
      whereClause.idc_product = { vendor: { in: brands } };
    }

    const productMatches = await prisma.product_matches.findMany({
      where: whereClause,
      include: {
        idc_product: true,
        competitor_product: {
          include: {
            competitor: true
          }
        },
        price_alerts: {
          where: { 
            status: { 
              notIn: ['resolved', 'dismissed'] 
            } 
          },
          take: 1
        }
      }
    });

    console.log(`📦 Scanning ${productMatches.length} product matches for violations`);

    for (const match of productMatches) {
      const { idc_product, competitor_product } = match;
      
      // Use iDC price as MAP (could be enhanced to have dedicated MAP field)
      const mapPrice = idc_product.price;
      const competitorPrice = competitor_product.price;

      if (!mapPrice || !competitorPrice) {
        continue;
      }

      const severity = detector.calculateViolationSeverity(mapPrice, competitorPrice);
      
      if (severity && (!severity_filter || severity === severity_filter)) {
        const impact = detector.calculateFinancialImpact(mapPrice, competitorPrice);
        
        const violationData = {
          product_match_id: match.id,
          alert_type: 'map_violation',
          title: `MAP Violation: ${competitor_product.title}`,
          message: `${competitor_product.competitor.name} is selling "${competitor_product.title}" for $${competitorPrice}, which is $${impact.price_gap.toFixed(2)} below the MAP price of $${mapPrice}`,
          severity: severity,
          old_price: mapPrice,
          new_price: competitorPrice,
          price_change: -impact.price_gap,
          status: 'unread'
        };

        // Create alert if requested and not in dry run
        if (create_alerts && !dry_run) {
          // Check if we already have an unresolved alert for this match
          const existingAlert = match.price_alerts.find(alert => 
            !['resolved', 'dismissed'].includes(alert.status)
          );
          
          if (!existingAlert) {
            await prisma.price_alerts.create({
              data: violationData
            });
          } else {
            // Update existing alert with latest data
            await prisma.price_alerts.update({
              where: { id: existingAlert.id },
              data: {
                ...violationData,
                updated_at: new Date()
              }
            });
          }
        }

        results.violations_found++;
        results.by_severity[severity]++;
        
        results.violations.push({
          match_id: match.id,
          idc_product: {
            title: idc_product.title,
            vendor: idc_product.vendor,
            sku: idc_product.sku,
            price: mapPrice
          },
          competitor_product: {
            title: competitor_product.title,
            vendor: competitor_product.vendor,
            sku: competitor_product.sku,
            price: competitorPrice,
            competitor: competitor_product.competitor.name,
            domain: competitor_product.competitor.domain
          },
          violation: {
            severity: severity,
            price_difference: impact.price_gap,
            percentage_below: impact.percentage_below.toFixed(2)
          }
        });
      }

      results.total_matches_scanned++;
    }

    console.log(`✅ Violation scan completed: ${results.violations_found} violations found from ${results.total_matches_scanned} matches`);

    res.json({
      message: `MAP violation scan completed${dry_run ? ' (dry run)' : ''}`,
      ...results
    });

  } catch (error) {
    console.error('Error scanning for MAP violations:', error);
    res.status(500).json({ error: 'Failed to scan for MAP violations' });
  }
});

// Get current violations with filtering
router.get('/violations', async (req, res) => {
  try {
    const { 
      severity, 
      brand,
      competitor,
      resolved = 'false',
      sort_by = 'severity',
      page = 1, 
      limit = 50 
    } = req.query;

    const skip = (parseInt(page) - 1) * parseInt(limit);
    const where = { 
      status: resolved === 'true' ? 'resolved' : { notIn: ['resolved', 'dismissed'] }
    };

    if (severity) {
      where.severity = severity;
    }

    if (brand || competitor) {
      where.product_match = {};
      if (brand) {
        where.product_match.idc_product = { vendor: brand };
      }
      if (competitor) {
        where.product_match.competitor_product = {
          competitor: {
            name: { contains: competitor, mode: 'insensitive' }
          }
        };
      }
    }

    // Define sort options
    const sortOptions = {
      'severity': [
        { severity: 'desc' },
        { price_change: 'desc' }
      ],
      'percentage': [
        { price_change: 'desc' }
      ],
      'amount': [
        { price_change: 'desc' }
      ],
      'recent': [
        { created_at: 'desc' }
      ]
    };

    const [violations, totalCount, summary] = await Promise.all([
      prisma.price_alerts.findMany({
        where,
        skip,
        take: parseInt(limit),
        include: {
          product_match: {
            include: {
              idc_product: true,
              competitor_product: {
                include: {
                  competitor: true
                }
              }
            }
          }
        },
        orderBy: sortOptions[sort_by] || sortOptions.severity
      }),
      prisma.price_alerts.count({ where }),
      // Get summary statistics
      prisma.price_alerts.groupBy({
        by: ['severity'],
        where: { 
          status: { 
            notIn: ['resolved', 'dismissed'] 
          } 
        },
        _count: { id: true },
        _sum: { 
          price_change: true
        }
      })
    ]);

    // Format summary
    const violationSummary = {
      total_active: summary.reduce((sum, s) => sum + s._count.id, 0),
      total_impact: summary.reduce((sum, s) => sum + Math.abs(s._sum.price_change || 0), 0),
      by_severity: {}
    };

    summary.forEach(s => {
      violationSummary.by_severity[s.severity] = {
        count: s._count.id,
        total_difference: Math.abs(s._sum.price_change || 0)
      };
    });

    res.json({
      violations,
      summary: violationSummary,
      pagination: {
        page: parseInt(page),
        limit: parseInt(limit),
        total: totalCount,
        total_pages: Math.ceil(totalCount / parseInt(limit)),
        has_next: skip + parseInt(limit) < totalCount,
        has_prev: parseInt(page) > 1
      }
    });

  } catch (error) {
    console.error('Error fetching MAP violations:', error);
    res.status(500).json({ error: 'Failed to fetch MAP violations' });
  }
});

// Get violation details
router.get('/violations/:violationId', async (req, res) => {
  try {
    const { violationId } = req.params;

    const violation = await prisma.price_alerts.findUnique({
      where: { id: violationId },
      include: {
        product_match: {
          include: {
            idc_product: true,
            competitor_product: {
              include: {
                competitor: true,
                price_history: {
                  orderBy: { recorded_at: 'desc' },
                  take: 10
                }
              }
            }
          }
        }
      }
    });

    if (!violation) {
      return res.status(404).json({ error: 'Violation not found' });
    }

    res.json(violation);

  } catch (error) {
    console.error('Error fetching violation details:', error);
    res.status(500).json({ error: 'Failed to fetch violation details' });
  }
});

// Resolve violation
router.post('/violations/:violationId/resolve', async (req, res) => {
  try {
    const { violationId } = req.params;
    const { resolution_note, resolved_by } = req.body;

    const violation = await prisma.price_alerts.findUnique({
      where: { id: violationId }
    });

    if (!violation) {
      return res.status(404).json({ error: 'Violation not found' });
    }

    if (violation.status === 'resolved') {
      return res.status(400).json({ error: 'Violation is already resolved' });
    }

    const updatedViolation = await prisma.price_alerts.update({
      where: { id: violationId },
      data: {
        status: 'resolved',
        updated_at: new Date()
      }
    });

    res.json({
      message: 'Violation resolved successfully',
      violation: updatedViolation
    });

  } catch (error) {
    console.error('Error resolving violation:', error);
    res.status(500).json({ error: 'Failed to resolve violation' });
  }
});

// Bulk resolve violations
router.post('/violations/bulk-resolve', async (req, res) => {
  try {
    const { violation_ids, resolution_note, resolved_by } = req.body;

    if (!violation_ids || !Array.isArray(violation_ids) || violation_ids.length === 0) {
      return res.status(400).json({ error: 'violation_ids array is required' });
    }

    const result = await prisma.price_alerts.updateMany({
      where: {
        id: { in: violation_ids },
        status: { 
          notIn: ['resolved', 'dismissed'] 
        }
      },
      data: {
        status: 'resolved',
        updated_at: new Date()
      }
    });

    res.json({
      message: `${result.count} violations resolved successfully`,
      resolved_count: result.count
    });

  } catch (error) {
    console.error('Error bulk resolving violations:', error);
    res.status(500).json({ error: 'Failed to bulk resolve violations' });
  }
});

// Get violation trends
router.get('/trends', async (req, res) => {
  try {
    const { 
      period = '7d',
      brand,
      competitor 
    } = req.query;

    // Calculate date range
    const now = new Date();
    const daysAgo = period === '30d' ? 30 : period === '7d' ? 7 : 1;
    const startDate = new Date(now.getTime() - (daysAgo * 24 * 60 * 60 * 1000));

    const where = {
      created_at: { gte: startDate }
    };

    if (brand || competitor) {
      where.product_match = {};
      if (brand) {
        where.product_match.idc_product = { vendor: brand };
      }
      if (competitor) {
        where.product_match.competitor_product = {
          competitor: {
            name: { contains: competitor, mode: 'insensitive' }
          }
        };
      }
    }

    // Get trend data
    const [dailyTrends, severityTrends, topViolators] = await Promise.all([
      // Daily violation counts
      prisma.$queryRaw`
        SELECT 
          DATE(created_at) as date,
          COUNT(*) as violation_count,
          AVG(ABS(price_change)) as avg_violation_pct,
          SUM(ABS(price_change)) as total_impact
        FROM price_alerts 
        WHERE created_at >= ${startDate}
        GROUP BY DATE(created_at)
        ORDER BY date ASC
      `,
      
      // Severity distribution over time
      prisma.price_alerts.groupBy({
        by: ['severity'],
        where,
        _count: { id: true },
        _sum: { price_change: true }
      }),

      // Top violating competitors - get from product_match relation
      prisma.price_alerts.findMany({
        where,
        select: {
          product_match: {
            select: {
              competitor_product: {
                select: {
                  competitor: {
                    select: { id: true, name: true, domain: true }
                  }
                }
              }
            }
          },
          price_change: true
        },
        take: 100
      })
    ]);

    // Process top violators from the fetched data
    const competitorStats = {};
    topViolators.forEach(alert => {
      if (alert.product_match?.competitor_product?.competitor) {
        const competitor = alert.product_match.competitor_product.competitor;
        if (!competitorStats[competitor.id]) {
          competitorStats[competitor.id] = {
            competitor,
            violation_count: 0,
            total_impact: 0
          };
        }
        competitorStats[competitor.id].violation_count++;
        competitorStats[competitor.id].total_impact += Math.abs(alert.price_change || 0);
      }
    });

    const topViolatorsWithNames = Object.values(competitorStats)
      .sort((a, b) => b.violation_count - a.violation_count)
      .slice(0, 10);

    res.json({
      period,
      date_range: {
        start: startDate.toISOString(),
        end: now.toISOString()
      },
      daily_trends: dailyTrends,
      severity_trends: severityTrends,
      top_violators: topViolatorsWithNames
    });

  } catch (error) {
    console.error('Error fetching violation trends:', error);
    res.status(500).json({ error: 'Failed to fetch violation trends' });
  }
});

export default router;