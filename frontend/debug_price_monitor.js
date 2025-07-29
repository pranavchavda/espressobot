import { PrismaClient } from '@prisma/client';
const prisma = new PrismaClient();

async function checkProductMatches() {
  try {
    console.log('=== PRODUCT MATCHES BY COMPETITOR ===');
    const matches = await prisma.product_matches.findMany({
      include: {
        competitor_product: {
          include: {
            competitor: true
          }
        }
      }
    });
    
    const matchesByCompetitor = {};
    const violationsByCompetitor = {};
    
    matches.forEach(match => {
      const competitorName = match.competitor_product.competitor.name;
      if (!matchesByCompetitor[competitorName]) {
        matchesByCompetitor[competitorName] = 0;
        violationsByCompetitor[competitorName] = 0;
      }
      matchesByCompetitor[competitorName]++;
      if (match.is_map_violation) {
        violationsByCompetitor[competitorName]++;
      }
    });
    
    console.table(Object.keys(matchesByCompetitor).map(name => ({
      competitor: name,
      total_matches: matchesByCompetitor[name],
      map_violations: violationsByCompetitor[name],
      violation_rate: violationsByCompetitor[name] > 0 ? (violationsByCompetitor[name] / matchesByCompetitor[name] * 100).toFixed(1) + '%' : '0%'
    })));
    
  } catch (error) {
    console.error('Error:', error);
  } finally {
    await prisma.$disconnect();
  }
}

async function checkPriceAlerts() {
  try {
    console.log('\n=== RECENT PRICE ALERTS BY COMPETITOR ===');
    const alerts = await prisma.price_alerts.findMany({
      include: {
        product_match: {
          include: {
            competitor_product: {
              include: {
                competitor: true
              }
            },
            idc_product: true
          }
        }
      },
      orderBy: { created_at: 'desc' },
      take: 20
    });
    
    if (alerts.length === 0) {
      console.log('No price alerts found');
      return;
    }
    
    const alertsByCompetitor = {};
    alerts.forEach(alert => {
      const competitorName = alert.product_match.competitor_product.competitor.name;
      if (!alertsByCompetitor[competitorName]) {
        alertsByCompetitor[competitorName] = 0;
      }
      alertsByCompetitor[competitorName]++;
    });
    
    console.table(Object.keys(alertsByCompetitor).map(name => ({
      competitor: name,
      recent_alerts: alertsByCompetitor[name]
    })));
    
    console.log('\n=== RECENT ALERTS DETAILS ===');
    alerts.slice(0, 10).forEach(alert => {
      console.log(`${alert.created_at.toISOString().split('T')[0]} - ${alert.product_match.competitor_product.competitor.name}: ${alert.title}`);
    });
    
  } catch (error) {
    console.error('Error:', error);
  } finally {
    await prisma.$disconnect();
  }
}

async function checkCompetitorProducts() {
  try {
    console.log('\n=== COMPETITOR PRODUCTS STATUS ===');
    const competitorProducts = await prisma.competitor_products.findMany({
      include: {
        competitor: true
      },
      orderBy: { scraped_at: 'desc' },
      take: 100
    });
    
    const productsByCompetitor = {};
    const recentProductsByCompetitor = {};
    const today = new Date();
    const threeDaysAgo = new Date(today.getTime() - 3 * 24 * 60 * 60 * 1000);
    
    competitorProducts.forEach(product => {
      const competitorName = product.competitor.name;
      if (!productsByCompetitor[competitorName]) {
        productsByCompetitor[competitorName] = 0;
        recentProductsByCompetitor[competitorName] = 0;
      }
      productsByCompetitor[competitorName]++;
      if (product.scraped_at > threeDaysAgo) {
        recentProductsByCompetitor[competitorName]++;
      }
    });
    
    console.table(Object.keys(productsByCompetitor).map(name => ({
      competitor: name,
      total_products: productsByCompetitor[name],
      recent_products: recentProductsByCompetitor[name]
    })));
    
    // Show recent products from each competitor
    console.log('\n=== RECENT COMPETITOR PRODUCTS (sample) ===');
    const competitors = await prisma.competitors.findMany({
      include: {
        competitor_products: {
          orderBy: { scraped_at: 'desc' },
          take: 3
        }
      }
    });
    
    competitors.forEach(competitor => {
      console.log(`\n${competitor.name}:`);
      competitor.competitor_products.forEach(product => {
        console.log(`  - ${product.title} ($${product.price}) [${product.scraped_at.toISOString().split('T')[0]}]`);
      });
    });
    
  } catch (error) {
    console.error('Error:', error);
  }
}

async function checkIdcProducts() {
  try {
    console.log('\n=== IDC PRODUCTS STATUS ===');
    const idcProducts = await prisma.idc_products.findMany({
      include: {
        monitored_brand: true
      },
      orderBy: { last_synced_at: 'desc' }
    });
    
    console.log(`Total IDC products: ${idcProducts.length}`);
    
    // Group by brand
    const brandCounts = {};
    idcProducts.forEach(product => {
      const brand = product.monitored_brand.brand_name;
      brandCounts[brand] = (brandCounts[brand] || 0) + 1;
    });
    
    console.log('\nIDC Products by Brand:');
    console.table(Object.keys(brandCounts).map(brand => ({
      brand: brand,
      count: brandCounts[brand]
    })));
    
  } catch (error) {
    console.error('Error:', error);
  }
}

async function checkCompetitorBrands() {
  try {
    console.log('\n=== COMPETITOR PRODUCTS BY BRAND ===');
    const competitorProducts = await prisma.competitor_products.findMany({
      include: {
        competitor: true
      }
    });
    
    const brandsByCompetitor = {};
    competitorProducts.forEach(product => {
      const competitorName = product.competitor.name;
      const brand = product.vendor;
      
      if (!brandsByCompetitor[competitorName]) {
        brandsByCompetitor[competitorName] = {};
      }
      brandsByCompetitor[competitorName][brand] = (brandsByCompetitor[competitorName][brand] || 0) + 1;
    });
    
    Object.keys(brandsByCompetitor).forEach(competitor => {
      console.log(`\n${competitor}:`);
      const brands = Object.keys(brandsByCompetitor[competitor]);
      brands.forEach(brand => {
        console.log(`  - ${brand}: ${brandsByCompetitor[competitor][brand]} products`);
      });
    });
    
  } catch (error) {
    console.error('Error:', error);
  }
}

async function main() {
  await checkProductMatches();
  await checkPriceAlerts();
  await checkCompetitorProducts();
  await checkIdcProducts();
  await checkCompetitorBrands();
}

main();