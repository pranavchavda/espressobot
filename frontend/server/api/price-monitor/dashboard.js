import express from 'express';
import prisma from '../../lib/prisma.js';

const router = express.Router();

// Simple overview endpoint for dashboard
router.get('/overview', async (req, res) => {
  try {
    const [
      totalIdcProducts,
      totalCompetitorProducts,
      totalMatches,
      activeViolations
    ] = await Promise.all([
      prisma.idc_products.count(),
      prisma.competitor_products.count(),
      prisma.product_matches.count(),
      prisma.price_alerts.count({
        where: { 
          status: { 
            notIn: ['resolved', 'dismissed'] 
          } 
        }
      })
    ]);

    // Get some recent activity
    const recentActivity = [
      {
        title: 'Product Sync',
        description: `${totalIdcProducts} products synced from Shopify`,
        created_at: new Date().toISOString()
      },
      {
        title: 'Product Matching',
        description: `${totalMatches} product matches found`,
        created_at: new Date().toISOString()
      },
      {
        title: 'Competitor Data',
        description: `${totalCompetitorProducts} competitor products tracked`,
        created_at: new Date().toISOString()
      }
    ];

    res.json({
      total_idc_products: totalIdcProducts,
      total_competitor_products: totalCompetitorProducts,
      total_matches: totalMatches,
      active_violations: activeViolations,
      recent_activity: recentActivity
    });
  } catch (error) {
    console.error('Error fetching dashboard overview:', error);
    res.status(500).json({ error: 'Failed to fetch dashboard overview' });
  }
});

// Get dashboard statistics
router.get('/stats', async (req, res) => {
  try {
    // Get basic counts
    const [
      totalMatches,
      activeViolations,
      totalCompetitors,
      totalIdcProducts,
      totalCompetitorProducts,
      activeBrands
    ] = await Promise.all([
      // Total product matches
      prisma.product_matches.count(),
      
      // Active MAP violations
      prisma.price_alerts.count({
        where: { 
          status: { 
            notIn: ['resolved', 'dismissed'] 
          } 
        }
      }),
      
      // Total active competitors
      prisma.competitors.count({
        where: { is_active: true }
      }),

      // Total iDC products
      prisma.idc_products.count(),

      // Total competitor products
      prisma.competitor_products.count(),

      // Active monitored brands
      prisma.monitored_brands.count({
        where: { is_active: true }
      })
    ]);

    // Calculate revenue at risk from MAP violations
    const violationAmounts = await prisma.price_alerts.aggregate({
      _sum: { price_change: true },
      where: { 
        status: { 
          notIn: ['resolved', 'dismissed'] 
        } 
      }
    });
    
    const revenueAtRisk = Math.abs(violationAmounts._sum.price_change || 0);

    // Find worst offender (competitor with most violations)
    const worstOffenderData = await prisma.price_alerts.findMany({
      where: { 
        status: { 
          notIn: ['resolved', 'dismissed'] 
        } 
      },
      select: {
        product_matches: {
          select: {
            competitor_products: {
              select: {
                competitors: {
                  select: { id: true, name: true, domain: true }
                }
              }
            }
          }
        },
        price_change: true
      }
    });

    let worstOffender = null;
    if (worstOffenderData.length > 0) {
      // Group by competitor to find worst offender
      const competitorViolations = {};
      worstOffenderData.forEach(alert => {
        if (alert.product_matches?.competitor_products?.competitors) {
          const competitor = alert.product_matches.competitor_products.competitors;
          if (!competitorViolations[competitor.id]) {
            competitorViolations[competitor.id] = {
              competitor,
              violations: 0,
              violation_amount: 0
            };
          }
          competitorViolations[competitor.id].violations++;
          competitorViolations[competitor.id].violation_amount += Math.abs(alert.price_change || 0);
        }
      });
      
      const worstCompetitor = Object.values(competitorViolations)
        .sort((a, b) => b.violations - a.violations)[0];
      
      if (worstCompetitor) {
        worstOffender = {
          name: worstCompetitor.competitor.name,
          domain: worstCompetitor.competitor.domain,
          violations: worstCompetitor.violations,
          violation_amount: worstCompetitor.violation_amount
        };
      }
    }

    // Get competitor status
    const competitors = await prisma.competitors.findMany({
      where: { is_active: true },
      include: {
        _count: {
          select: { competitor_products: true }
        }
      }
    });

    const competitorStatus = competitors.map(competitor => ({
      name: competitor.name,
      domain: competitor.domain,
      status: 'Active',
      last_updated: competitor.last_scraped_at 
        ? getTimeAgo(competitor.last_scraped_at)
        : 'Never',
      products_tracked: competitor._count.competitor_products,
      avg_price_difference: 0 // TODO: Calculate this from matches
    }));

    // Get recent alerts (MAP violations)
    const recentViolations = await prisma.price_alerts.findMany({
      where: { 
        status: { 
          notIn: ['resolved', 'dismissed'] 
        } 
      },
      // No limit - show all recent violations
      orderBy: { created_at: 'desc' },
      include: {
        product_matches: {
          include: {
            idc_products: true,
            competitor_products: {
              include: { competitors: true }
            }
          }
        }
      }
    });

    const recentAlerts = recentViolations.map(violation => ({
      id: violation.id,
      product_title: violation.product_matches?.competitor_products?.title || 'Unknown Product',
      competitor: violation.product_matches?.competitor_products?.competitors?.name || 'Unknown Competitor',
      alert_type: violation.alert_type || 'map_violation',
      severity: violation.severity,
      map_price: parseFloat(violation.old_price || 0),
      competitor_price: parseFloat(violation.new_price || 0),
      price_difference: Math.abs(parseFloat(violation.price_change || 0)),
      created_at: violation.created_at
    }));

    const stats = {
      products_monitored: totalMatches,
      idc_products: totalIdcProducts,
      competitor_products: totalCompetitorProducts,
      active_brands: activeBrands,
      active_alerts: activeViolations,
      competitors_tracked: totalCompetitors,
      map_violations: activeViolations,
      revenue_at_risk: parseFloat(revenueAtRisk),
      worst_offender: worstOffender
    };

    res.json({
      stats,
      competitor_status: competitorStatus,
      recent_alerts: recentAlerts
    });
  } catch (error) {
    console.error('Error fetching dashboard stats:', error);
    res.status(500).json({ error: 'Failed to fetch dashboard stats' });
  }
});

// Get summary statistics for charts/graphs
router.get('/summary', async (req, res) => {
  try {
    const { period = '7d' } = req.query;
    
    // Calculate date range based on period
    const now = new Date();
    let startDate;
    
    switch (period) {
      case '24h':
        startDate = new Date(now.getTime() - 24 * 60 * 60 * 1000);
        break;
      case '7d':
        startDate = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
        break;
      case '30d':
        startDate = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
        break;
      default:
        startDate = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
    }

    // Get violations over time
    const violationsOverTime = await prisma.price_alerts.findMany({
      where: {
        created_at: { gte: startDate },
        status: { 
          notIn: ['resolved', 'dismissed'] 
        }
      },
      select: {
        created_at: true,
        severity: true,
        price_change: true
      },
      orderBy: { created_at: 'asc' }
    });

    // Get competitor performance
    const competitorPerformanceData = await prisma.price_alerts.findMany({
      where: { 
        created_at: { gte: startDate },
        status: { 
          notIn: ['resolved', 'dismissed'] 
        }
      },
      select: {
        product_matches: {
          select: {
            competitor_products: {
              select: {
                competitors: {
                  select: { id: true, name: true, domain: true }
                }
              }
            }
          }
        },
        price_change: true
      }
    });

    // Process competitor performance data
    const competitorPerformance = {};
    competitorPerformanceData.forEach(alert => {
      if (alert.product_match?.competitor_product?.competitor) {
        const competitor = alert.product_match.competitor_product.competitor;
        if (!competitorPerformance[competitor.id]) {
          competitorPerformance[competitor.id] = {
            competitor_name: competitor.name,
            competitor_domain: competitor.domain,
            violation_count: 0,
            total_violation_amount: 0
          };
        }
        competitorPerformance[competitor.id].violation_count++;
        competitorPerformance[competitor.id].total_violation_amount += Math.abs(alert.price_change || 0);
      }
    });

    const competitorPerformanceWithNames = Object.values(competitorPerformance)
      .sort((a, b) => b.violation_count - a.violation_count);

    res.json({
      period,
      violations_over_time: violationsOverTime,
      competitor_performance: competitorPerformanceWithNames
    });
  } catch (error) {
    console.error('Error fetching dashboard summary:', error);
    res.status(500).json({ error: 'Failed to fetch dashboard summary' });
  }
});

// Helper function to calculate time ago
function getTimeAgo(date) {
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMinutes = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffMinutes < 60) {
    return `${diffMinutes}m ago`;
  } else if (diffHours < 24) {
    return `${diffHours}h ago`;
  } else {
    return `${diffDays}d ago`;
  }
}

export default router;