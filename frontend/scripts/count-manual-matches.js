import { PrismaClient } from '@prisma/client';
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

dotenv.config({ path: path.join(__dirname, '../.env') });

const prisma = new PrismaClient();

async function countMatches() {
  const totalMatches = await prisma.product_matches.count();
  const manualMatches = await prisma.product_matches.count({
    where: { is_manual_match: true }
  });
  const autoMatches = await prisma.product_matches.count({
    where: { is_manual_match: false }
  });
  
  console.log(`Total matches: ${totalMatches}`);
  console.log(`Manual matches: ${manualMatches}`);
  console.log(`Automated matches: ${autoMatches}`);
  
  await prisma.$disconnect();
  process.exit(0);
}

countMatches().catch(error => {
  console.error('Error:', error);
  prisma.$disconnect();
  process.exit(1);
});