import { PrismaClient } from '@prisma/client';
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Load environment variables
dotenv.config({ path: path.join(__dirname, '../.env') });

const prisma = new PrismaClient();

// Manual matches to create
const manualMatches = [
  // Batch 1 - Profitec
  { idc: "Profitec RIDE Dual Boiler Espresso Machine", comp: "Profitec RIDE Dual Boiler Espresso Machine", vendor: "The Kitchen Barista" },
  { idc: "Profitec RIDE Dual Boiler Espresso Machine", comp: "Profitec - RIDE Dual Boiler Espresso Machine", vendor: "Cafe Liegeois" },
  { idc: "Profitec Twist A54 Espresso Grinder", comp: "Profitec Twist A54 Coffee Grinder", vendor: "HomeCoffeeSolutions.com" },
  { idc: "Profitec Twist A54 Espresso Grinder", comp: "Profitec - Twist A54", vendor: "Cafe Liegeois" },
  { idc: "Profitec JUMP Espresso Machine", comp: "Profitec Jump Espresso Machine", vendor: "The Kitchen Barista" },
  { idc: "Profitec Pro 400 Espresso Machine - White", comp: "Profitec Pro 400 Espresso Machine", vendor: "The Kitchen Barista" },
  { idc: "Profitec Pro 400 Espresso Machine - White", comp: "Profitec - Pro 400 - Espresso Machine", vendor: "Cafe Liegeois" },
  
  // Batch 2 - More Profitec
  { idc: "Profitec Pro 400 Espresso Machine - Black", comp: "Profitec Pro 400 Heat Exchanger Espresso Machine With E61 Group Head & PID Temperature Control (Black)", vendor: "HomeCoffeeSolutions.com" },
  { idc: "Profitec Go Espresso Machine - Brushed Stainless Steel", comp: "Profitec Go Single Boiler PID Espresso Machine (Brushed Stainless Steel)", vendor: "HomeCoffeeSolutions.com" },
  { idc: "Profitec GO Espresso Machine - Blue", comp: "Profitec Go Single Boiler PID Espresso Machine (Blue)", vendor: "HomeCoffeeSolutions.com" },
  { idc: "Profitec Go Espresso Machine - Yellow", comp: "Profitec Go Single Boiler PID Espresso Machine (Yellow)", vendor: "HomeCoffeeSolutions.com" },
  
  // Batch 3 - All matched
  { idc: "Profitec Go Espresso Machine - Red", comp: "Profitec Go Single Boiler PID Espresso Machine (Red)", vendor: "HomeCoffeeSolutions.com" },
  { idc: "Profitec Go Espresso Machine - Red", comp: "Profitec Go Espresso Machine (Red)", vendor: "The Kitchen Barista" },
  { idc: "Profitec Go Espresso Machine - Black", comp: "Profitec Go Single Boiler PID Espresso Machine (Black)", vendor: "HomeCoffeeSolutions.com" },
  { idc: "Profitec Go Espresso Machine - Black", comp: "Profitec Go Espresso Machine (Black)", vendor: "The Kitchen Barista" },
  { idc: "Profitec Milk Frothing Pitcher - 500 ml", comp: "Profitec Milk Frothing Pitcher(500ml)", vendor: "HomeCoffeeSolutions.com" },
  { idc: "Profitec Pro 400 Espresso Machine", comp: "Profitec Pro 400 Heat Exchanger Espresso Machine With E61 Group Head & PID Temperature Control (Black)", vendor: "HomeCoffeeSolutions.com" },
  { idc: "Profitec Pro 400 Espresso Machine", comp: "Profitec Pro 400 Espresso Machine", vendor: "The Kitchen Barista" },
  { idc: "Profitec Pro 400 Espresso Machine", comp: "Profitec - Pro 400 - Espresso Machine", vendor: "Cafe Liegeois" },
  { idc: "Profitec Pro 800 Espresso Machine", comp: "Profitec Pro 800 Lever Espresso Machine With PID Temperature Control", vendor: "HomeCoffeeSolutions.com" },
  { idc: "Profitec Pro 800 Espresso Machine", comp: "Profitec Pro 800 Lever Espresso Machine 2022 Version (Stainless Steel)", vendor: "The Kitchen Barista" },
  { idc: "Profitec Pro 800 Espresso Machine", comp: "Profitec - Pro 800", vendor: "Cafe Liegeois" },
  { idc: "Profitec Pro T64 Coffee Grinder", comp: "Profitec Pro T64 Coffee Grinder", vendor: "HomeCoffeeSolutions.com" },
  { idc: "Profitec Pro T64 Coffee Grinder", comp: "Profitec Pro T64 Flat Burr Grinder (Stainless Steel)", vendor: "The Kitchen Barista" },
  { idc: "Profitec Pro T64 Coffee Grinder", comp: "Profitec - Pro T64 Grinder", vendor: "Cafe Liegeois" },
  { idc: "Profitec Pro 500 Espresso Machine w/ Quick Steam", comp: "Profitec Pro 500 Heat Exchanger & Quick Steam Espresso Machine With E61 Group Head, PID Temperature Control", vendor: "HomeCoffeeSolutions.com" },
  { idc: "Profitec Pro 500 Espresso Machine w/ Quick Steam", comp: "Profitec Pro 500 Espresso Machine w/ Quick Steam", vendor: "The Kitchen Barista" },
  { idc: "Profitec Tamping Pad", comp: "Profitec Tamping Pad", vendor: "HomeCoffeeSolutions.com" },
  { idc: "Profitec Tamping Pad", comp: "Profitec Tamping Pad (Black)", vendor: "The Kitchen Barista" },
  { idc: "Profitec Pro 500 Espresso Machine w/ PID and Flow Control", comp: "Profitec Pro 500 Heat Exchanger Espresso Machine With E61 Group Head, PID Temperature Control, & Flow Control", vendor: "HomeCoffeeSolutions.com" },
  { idc: "Profitec Pro 500 Espresso Machine w/ PID and Flow Control", comp: "Profitec Pro 500 Espresso Machine w/ PID and Flow Control", vendor: "The Kitchen Barista" },
  { idc: "Profitec E61 Flow Control Device", comp: "Profitec E61 Flow Control Device", vendor: "The Kitchen Barista" },
  
  // Batch 4 - Eureka
  { idc: "Profitec Pro 500 Espresso Machine w/ PID", comp: "Profitec Pro 500 Espresso Machine w/ PID", vendor: "The Kitchen Barista" },
  { idc: "Profitec Pro 500 Espresso Machine w/ PID", comp: "Profitec Pro 500 Heat Exchanger Espresso Machine With E61 Group Head & PID Temperature Control", vendor: "HomeCoffeeSolutions.com" },
  { idc: "Eureka Mignon Zero - Blue", comp: "Eureka Mignon Zero | Single Dose Coffee Grinder (Blue)", vendor: "HomeCoffeeSolutions.com" },
  { idc: "Eureka Mignon Zero - Pale Blue", comp: "Eureka Mignon Zero Grinder (Pale Blue)", vendor: "The Kitchen Barista" },
  { idc: "Eureka Mignon Zero - Silver", comp: "Eureka Mignon Zero | Single Dose Coffee Grinder (Chrome)", vendor: "HomeCoffeeSolutions.com" },
  { idc: "Eureka Mignon Zero - Silver", comp: "Eureka Mignon Zero Grinder (Chrome)", vendor: "The Kitchen Barista" },
  { idc: "Eureka Mignon Zero - Yellow", comp: "Eureka Mignon Zero Grinder (Yellow)", vendor: "The Kitchen Barista" },
  { idc: "Eureka Mignon Zero - Red", comp: "Eureka Mignon Zero Grinder (Red)", vendor: "The Kitchen Barista" },
  { idc: "Eureka Mignon Zero - Red", comp: "Eureka Mignon Zero | Single Dose Coffee Grinder (Ferrari Red)", vendor: "HomeCoffeeSolutions.com" },
  { idc: "Eureka Mignon Libra 65 AP Grind by Weight - Silver", comp: "Eureka Mignon Libra 65 AP Grinder with Grind by Weight (Chrome)", vendor: "The Kitchen Barista" },
  
  // Batch 5 - More Eureka
  { idc: "Eureka Mignon Zero - Black w/ Black Spout", comp: "Eureka Mignon Zero Grinder with Black Spout (Matte Black)", vendor: "The Kitchen Barista" },
  { idc: "Eureka Mignon Zero - Black w/ Black Spout", comp: "Eureka Mignon Zero | Single Dose Coffee Grinder (Black with Black Spout)", vendor: "HomeCoffeeSolutions.com" },
  { idc: "Eureka Mignon Zero - White w/ Black Spout", comp: "Eureka Mignon Zero Grinder with Black Spout (White)", vendor: "The Kitchen Barista" },
  { idc: "Eureka Mignon Zero 65 AP - Chrome", comp: "Eureka Mignon Zero 65 All Purpose Grinder (Chrome)", vendor: "The Kitchen Barista" },
  { idc: "Eureka Mignon Zero 65 AP - Chrome", comp: "Eureka Mignon Zero 65 All Purpose Grinder (Chrome) - BACKORDERED", vendor: "HomeCoffeeSolutions.com" },
  { idc: "Eureka Mignon Zero 65 AP - White", comp: "Eureka Mignon Zero 65 All Purpose Grinder (White)", vendor: "The Kitchen Barista" },
  { idc: "Eureka Mignon Zero 65 AP - White", comp: "Eureka Mignon Zero 65 All Purpose Grinder (White) - BACKORDERED", vendor: "HomeCoffeeSolutions.com" },
  { idc: "Eureka Mignon Zero 65 AP - White", comp: "Eureka - Zero 65 AP - White (OPEN BOX)", vendor: "Cafe Liegeois" },
  { idc: "Eureka Mignon Libra 65 AP Grind by Weight - Chrome", comp: "Eureka Mignon Libra 65 AP Grinder with Grind by Weight (Chrome)", vendor: "The Kitchen Barista" },
  
  // Batch 6
  { idc: "Eureka Mignon Libra 65 AP Grind by Weight - Black", comp: "Eureka Mignon Libra 65 AP Grinder with Grind by Weight (Black)", vendor: "The Kitchen Barista" },
  { idc: "Eureka Mignon Libra 65 AP Grind by Weight - Black", comp: "Eureka - Mignon Libra 65 AP - Grind by Weight", vendor: "Cafe Liegeois" },
  { idc: "Eureka Mignon Zero 65 AP - Black", comp: "Eureka - Zero 65 AP", vendor: "Cafe Liegeois" },
  { idc: "Eureka Mignon Silenzio 55 Grinder - Pale Blue", comp: "Eureka Mignon Silenzio Flat Burr Coffee Grinder (Pale Blue)", vendor: "The Kitchen Barista" },
  { idc: "Eureka Mignon Silenzio 55 Grinder - Pale Blue", comp: "Eureka Mignon Silenzio 55mm Grinder (Pale Blue)", vendor: "HomeCoffeeSolutions.com" },
  { idc: "Eureka Mignon Silenzio 55 Grinder - Red", comp: "Eureka Mignon Silenzio 55mm Grinder (Red)", vendor: "HomeCoffeeSolutions.com" },
  
  // Batch 7 - All matched
  { idc: "Eureka Mignon Silenzio 55 Grinder - White", comp: "Eureka Mignon Silenzio 55mm Grinder (White)", vendor: "HomeCoffeeSolutions.com" },
  { idc: "Eureka Mignon Silenzio 55 Grinder - White", comp: "Eureka Mignon Silenzio 55 Flat Burr Coffee Grinder (White)", vendor: "The Kitchen Barista" },
  { idc: "Eureka Mignon Silenzio 55 Grinder - Silver", comp: "Eureka Mignon Silenzio 55 Flat Burr Coffee Grinder (Grey/Silver)", vendor: "The Kitchen Barista" },
  { idc: "Eureka Mignon Silenzio 55 Grinder - Amaranth", comp: "Eureka Mignon Silenzio 55 Flat Burr Coffee Grinder (Amaranth)", vendor: "The Kitchen Barista" },
  { idc: "Eureka Mignon Silenzio 55 Grinder - Matte Black", comp: "Eureka Mignon Silenzio 55mm Grinder (Matte Black)", vendor: "HomeCoffeeSolutions.com" },
  { idc: "Eureka Atom W 65 Grind By Weight Espresso Grinder - White", comp: "Eureka Atom W 65 Grind By Weight Coffee Grinder (White)", vendor: "The Kitchen Barista" },
  { idc: "Eureka Atom W 75 Grind By Weight Espresso Grinder - White", comp: "Eureka Atom W 75 Grind By Weight Coffee Grinder (White)", vendor: "The Kitchen Barista" },
  { idc: "Eureka Atom Excellence 75 Burr Grinder - Red", comp: "Eureka Atom Excellence 75 Coffee Grinder (Red)", vendor: "The Kitchen Barista" },
  { idc: "Eureka Atom Excellence 65 Grinder - Ferrari Red", comp: "Eureka Atom Excellence 65 Coffee Grinder (Ferrari Red)", vendor: "The Kitchen Barista" },
  { idc: "Eureka Atom Excellence 65 Grinder - Grey", comp: "Eureka Atom Excellence 65 Coffee Grinder (Grey)", vendor: "The Kitchen Barista" },
  { idc: "Eureka Atom Excellence 75 Burr Grinder - White", comp: "Eureka Atom Excellence 75 Coffee Grinder (White)", vendor: "The Kitchen Barista" },
  
  // Batch 8
  { idc: "Eureka Atom Excellence 75 Burr Grinder - Matte Black", comp: "Eureka Atom Excellence 75 Coffee Grinder (Matte Black)", vendor: "The Kitchen Barista" },
  { idc: "Eureka Atom Excellence 75 Burr Grinder - Grey", comp: "Eureka Atom Excellence 75 Coffee Grinder (Grey)", vendor: "The Kitchen Barista" },
  { idc: "Eureka Mignon Libra Espresso Grinder w/ Grind by Weight - White", comp: "Eureka Mignon Libra Grinder with Grind by Weight (White)", vendor: "The Kitchen Barista" },
  
  // Batch 9
  { idc: "Eureka Mignon Zero - Chrome", comp: "Eureka Mignon Zero | Single Dose Coffee Grinder (Chrome)", vendor: "HomeCoffeeSolutions.com" },
  { idc: "Eureka Mignon Zero - Chrome", comp: "Eureka Mignon Zero Grinder (Chrome)", vendor: "The Kitchen Barista" },
  { idc: "Eureka Mignon Zero - Matte Black", comp: "Eureka Mignon Zero | Single Dose Coffee Grinder (Matte Black)", vendor: "HomeCoffeeSolutions.com" },
  { idc: "Eureka Mignon Zero - Matte Black", comp: "Eureka Mignon Zero Grinder (Matte Black)", vendor: "The Kitchen Barista" },
  { idc: "Eureka Mignon Zero - White", comp: "Eureka Mignon Zero | Single Dose Coffee Grinder (White)", vendor: "HomeCoffeeSolutions.com" },
  { idc: "Eureka Mignon Zero - White", comp: "Eureka Mignon Zero Grinder (White)", vendor: "The Kitchen Barista" },
  { idc: "Eureka Mignon Zero - Anthracite", comp: "Eureka Mignon Zero | Single Dose Coffee Grinder (Anthracite)", vendor: "HomeCoffeeSolutions.com" },
  { idc: "Eureka Mignon Zero - Anthracite", comp: "Eureka Mignon Zero Grinder (Anthracite)", vendor: "The Kitchen Barista" },
  { idc: "Eureka Zenith 65 Neo - Chrome", comp: "Eureka Zenith 65 Neo (Chrome)", vendor: "HomeCoffeeSolutions.com" },
  { idc: "Eureka Zenith 65 Neo - Chrome", comp: "Eureka Zenith 65 Neo (Chrome)", vendor: "The Kitchen Barista" },
  { idc: "Eureka Mignon Single Dose Hopper", comp: "Eureka Mignon Single Dose Hopper", vendor: "Cafe Liegeois" },
  { idc: "Eureka Mignon Single Dose Hopper", comp: "Eureka Mignon Single Dose Hopper (45g)", vendor: "HomeCoffeeSolutions.com" },
  { idc: "Eureka Zenith 65 Neo - White", comp: "Eureka Zenith 65 Neo (White)", vendor: "HomeCoffeeSolutions.com" },
  { idc: "Eureka Zenith 65 Neo - White", comp: "Eureka Zenith 65 Neo (White)", vendor: "The Kitchen Barista" },
  { idc: "Eureka Helios 65 Espresso Grinder - White", comp: "Eureka - Helios 65 Espresso Grinder", vendor: "Cafe Liegeois" },
  
  // Batch 10
  { idc: "Eureka Mignon Brew Pro Burr Grinder - White", comp: "Eureka Mignon Brew Pro Coffee Grinder (White)", vendor: "The Kitchen Barista" },
  { idc: "Eureka Mignon Brew Pro Burr Grinder - White", comp: "Eureka Mignon Brew Pro l Quiet 55mm Flat Burr Grinder (White)", vendor: "HomeCoffeeSolutions.com" },
  { idc: "Eureka Mignon Facile Grinder - White", comp: "Eureka Mignon Facile Grinder (White)", vendor: "HomeCoffeeSolutions.com" },
  { idc: "Eureka Mignon Facile Grinder - White", comp: "Eureka Mignon Facile Flat Burr Coffee Grinder (White)", vendor: "The Kitchen Barista" },
  { idc: "Eureka Mignon Crono Burr Grinder - Matte Black", comp: "Eureka Mignon Crono Burr Grinder (Matte Black)", vendor: "The Kitchen Barista" },
  { idc: "Eureka Mignon Crono Burr Grinder - Matte Black", comp: "Eureka Mignon Crono Burr Grinder (Matte Black)", vendor: "HomeCoffeeSolutions.com" },
  { idc: "Eureka Mignon Facile Grinder - Black", comp: "Eureka Mignon Facile 50mm Grinder (Matte Black)", vendor: "HomeCoffeeSolutions.com" },
  { idc: "Eureka Mignon Facile Grinder - Black", comp: "Eureka Mignon Facile Flat Burr Coffee Grinder (Matte Black)", vendor: "The Kitchen Barista" },
  { idc: "Eureka Zenith 65 Neo - Black", comp: "Eureka Zenith 65 Neo (Matte Black)", vendor: "The Kitchen Barista" },
  { idc: "Eureka Zenith 65 Neo - Black", comp: "Eureka Zenith 65 Neo (Matte Black)", vendor: "HomeCoffeeSolutions.com" },
  { idc: "Eureka Dosing Cup", comp: "Eureka Dosing Cup (45g)", vendor: "HomeCoffeeSolutions.com" },
  { idc: "ECM/Profitec AquaAroma Crema Water Softener", comp: "ECM/Profitec AquaAroma Crema Water Softener", vendor: "Cafe Liegeois" }
];

async function addManualMatches() {
  console.log(`Creating ${manualMatches.length} manual matches...`);
  
  let created = 0;
  let failed = 0;
  
  for (const match of manualMatches) {
    try {
      // Find IDC product
      const idcProduct = await prisma.idc_products.findFirst({
        where: { title: match.idc }
      });
      
      if (!idcProduct) {
        console.log(`❌ IDC product not found: ${match.idc}`);
        failed++;
        continue;
      }
      
      // Find competitor
      const competitor = await prisma.competitors.findFirst({
        where: { name: match.vendor }
      });
      
      if (!competitor) {
        console.log(`❌ Competitor not found: ${match.vendor}`);
        failed++;
        continue;
      }
      
      // Find competitor product
      const competitorProduct = await prisma.competitor_products.findFirst({
        where: {
          title: match.comp,
          competitor_id: competitor.id
        }
      });
      
      if (!competitorProduct) {
        console.log(`❌ Competitor product not found: ${match.comp} at ${match.vendor}`);
        failed++;
        continue;
      }
      
      // Create match
      const matchData = {
        id: `${idcProduct.id}_${competitorProduct.id}`,
        idc_product_id: idcProduct.id,
        competitor_product_id: competitorProduct.id,
        overall_score: 1.0,
        brand_similarity: 1.0,
        title_similarity: 1.0,
        embedding_similarity: 0.95,
        price_similarity: 0.95,
        confidence_level: 'high',
        is_manual_match: true,
        created_at: new Date(),
        updated_at: new Date()
      };
      
      await prisma.product_matches.upsert({
        where: {
          idc_product_id_competitor_product_id: {
            idc_product_id: idcProduct.id,
            competitor_product_id: competitorProduct.id
          }
        },
        create: matchData,
        update: {
          ...matchData,
          updated_at: new Date()
        }
      });
      
      console.log(`✅ Created match: ${match.idc} → ${match.comp} (${match.vendor})`);
      created++;
      
    } catch (error) {
      console.error(`❌ Error creating match: ${error.message}`);
      failed++;
    }
  }
  
  console.log(`\n✅ Successfully created: ${created} matches`);
  console.log(`❌ Failed: ${failed} matches`);
  
  await prisma.$disconnect();
  process.exit(0);
}

// Run the script
addManualMatches().catch(error => {
  console.error('Script error:', error);
  prisma.$disconnect();
  process.exit(1);
});