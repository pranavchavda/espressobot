import { PrismaClient } from '@prisma/client';
const prisma = new PrismaClient();

async function checkMatchesByCompetitor() {
  try {
    console.log('=== CURRENT MATCHES BY COMPETITOR ===');
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
    
    console.log(`\nTotal matches: ${matches.length}`);
    
  } catch (error) {
    console.error('Error:', error);
  } finally {
    await prisma.$disconnect();
  }
}

checkMatchesByCompetitor();