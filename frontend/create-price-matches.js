// Script to create manual price matches via API

const matches = [
  // Batch 1 - Profitec machines
  { idc_title: "Profitec RIDE Dual Boiler Espresso Machine", competitor_title: "Profitec RIDE Dual Boiler Espresso Machine", competitor: "The Kitchen Barista" },
  { idc_title: "Profitec RIDE Dual Boiler Espresso Machine", competitor_title: "Profitec - RIDE Dual Boiler Espresso Machine", competitor: "Cafe Liegeois" },
  { idc_title: "Profitec Twist A54 Espresso Grinder", competitor_title: "Profitec Twist A54 Coffee Grinder", competitor: "HomeCoffeeSolutions.com" },
  { idc_title: "Profitec Twist A54 Espresso Grinder", competitor_title: "Profitec - Twist A54", competitor: "Cafe Liegeois" },
  { idc_title: "Profitec JUMP Espresso Machine", competitor_title: "Profitec Jump Espresso Machine", competitor: "The Kitchen Barista" },
  { idc_title: "Profitec Pro 400 Espresso Machine - White", competitor_title: "Profitec Pro 400 Espresso Machine", competitor: "The Kitchen Barista" },
  { idc_title: "Profitec Pro 400 Espresso Machine - White", competitor_title: "Profitec - Pro 400 - Espresso Machine", competitor: "Cafe Liegeois" },
  
  // Batch 2
  { idc_title: "Profitec Pro 400 Espresso Machine - Black", competitor_title: "Profitec Pro 400 Heat Exchanger Espresso Machine With E61 Group Head & PID Temperature Control (Black)", competitor: "HomeCoffeeSolutions.com" },
  { idc_title: "Profitec Go Espresso Machine - Brushed Stainless Steel", competitor_title: "Profitec Go Single Boiler PID Espresso Machine (Brushed Stainless Steel)", competitor: "HomeCoffeeSolutions.com" },
  { idc_title: "Profitec GO Espresso Machine - Blue", competitor_title: "Profitec Go Single Boiler PID Espresso Machine (Blue)", competitor: "HomeCoffeeSolutions.com" },
  { idc_title: "Profitec Go Espresso Machine - Yellow", competitor_title: "Profitec Go Single Boiler PID Espresso Machine (Yellow)", competitor: "HomeCoffeeSolutions.com" },
  
  // Batch 3 - All 10 matched
  { idc_title: "Profitec Go Espresso Machine - Red", competitor_title: "Profitec Go Single Boiler PID Espresso Machine (Red)", competitor: "HomeCoffeeSolutions.com" },
  { idc_title: "Profitec Go Espresso Machine - Red", competitor_title: "Profitec Go Espresso Machine (Red)", competitor: "The Kitchen Barista" },
  { idc_title: "Profitec Go Espresso Machine - Black", competitor_title: "Profitec Go Single Boiler PID Espresso Machine (Black)", competitor: "HomeCoffeeSolutions.com" },
  { idc_title: "Profitec Go Espresso Machine - Black", competitor_title: "Profitec Go Espresso Machine (Black)", competitor: "The Kitchen Barista" },
  { idc_title: "Profitec Milk Frothing Pitcher - 500 ml", competitor_title: "Profitec Milk Frothing Pitcher(500ml)", competitor: "HomeCoffeeSolutions.com" },
  { idc_title: "Profitec Pro 400 Espresso Machine", competitor_title: "Profitec Pro 400 Heat Exchanger Espresso Machine With E61 Group Head & PID Temperature Control (Black)", competitor: "HomeCoffeeSolutions.com" },
  { idc_title: "Profitec Pro 400 Espresso Machine", competitor_title: "Profitec Pro 400 Espresso Machine", competitor: "The Kitchen Barista" },
  { idc_title: "Profitec Pro 400 Espresso Machine", competitor_title: "Profitec - Pro 400 - Espresso Machine", competitor: "Cafe Liegeois" },
  { idc_title: "Profitec Pro 800 Espresso Machine", competitor_title: "Profitec Pro 800 Lever Espresso Machine With PID Temperature Control", competitor: "HomeCoffeeSolutions.com" },
  { idc_title: "Profitec Pro 800 Espresso Machine", competitor_title: "Profitec Pro 800 Lever Espresso Machine 2022 Version (Stainless Steel)", competitor: "The Kitchen Barista" },
  { idc_title: "Profitec Pro 800 Espresso Machine", competitor_title: "Profitec - Pro 800", competitor: "Cafe Liegeois" },
  { idc_title: "Profitec Pro T64 Coffee Grinder", competitor_title: "Profitec Pro T64 Coffee Grinder", competitor: "HomeCoffeeSolutions.com" },
  { idc_title: "Profitec Pro T64 Coffee Grinder", competitor_title: "Profitec Pro T64 Flat Burr Grinder (Stainless Steel)", competitor: "The Kitchen Barista" },
  { idc_title: "Profitec Pro T64 Coffee Grinder", competitor_title: "Profitec - Pro T64 Grinder", competitor: "Cafe Liegeois" },
  { idc_title: "Profitec Pro 500 Espresso Machine w/ Quick Steam", competitor_title: "Profitec Pro 500 Heat Exchanger & Quick Steam Espresso Machine With E61 Group Head, PID Temperature Control", competitor: "HomeCoffeeSolutions.com" },
  { idc_title: "Profitec Pro 500 Espresso Machine w/ Quick Steam", competitor_title: "Profitec Pro 500 Espresso Machine w/ Quick Steam", competitor: "The Kitchen Barista" },
  { idc_title: "Profitec Tamping Pad", competitor_title: "Profitec Tamping Pad", competitor: "HomeCoffeeSolutions.com" },
  { idc_title: "Profitec Tamping Pad", competitor_title: "Profitec Tamping Pad (Black)", competitor: "The Kitchen Barista" },
  { idc_title: "Profitec Pro 500 Espresso Machine w/ PID and Flow Control", competitor_title: "Profitec Pro 500 Heat Exchanger Espresso Machine With E61 Group Head, PID Temperature Control, & Flow Control", competitor: "HomeCoffeeSolutions.com" },
  { idc_title: "Profitec Pro 500 Espresso Machine w/ PID and Flow Control", competitor_title: "Profitec Pro 500 Espresso Machine w/ PID and Flow Control", competitor: "The Kitchen Barista" },
  { idc_title: "Profitec E61 Flow Control Device", competitor_title: "Profitec E61 Flow Control Device", competitor: "The Kitchen Barista" },
  
  // Batch 4 - Eureka grinders
  { idc_title: "Profitec Pro 500 Espresso Machine w/ PID", competitor_title: "Profitec Pro 500 Espresso Machine w/ PID", competitor: "The Kitchen Barista" },
  { idc_title: "Profitec Pro 500 Espresso Machine w/ PID", competitor_title: "Profitec Pro 500 Heat Exchanger Espresso Machine With E61 Group Head & PID Temperature Control", competitor: "HomeCoffeeSolutions.com" },
  { idc_title: "Eureka Mignon Zero - Blue", competitor_title: "Eureka Mignon Zero | Single Dose Coffee Grinder (Blue)", competitor: "HomeCoffeeSolutions.com" },
  { idc_title: "Eureka Mignon Zero - Pale Blue", competitor_title: "Eureka Mignon Zero Grinder (Pale Blue)", competitor: "The Kitchen Barista" },
  { idc_title: "Eureka Mignon Zero - Silver", competitor_title: "Eureka Mignon Zero | Single Dose Coffee Grinder (Chrome)", competitor: "HomeCoffeeSolutions.com" },
  { idc_title: "Eureka Mignon Zero - Silver", competitor_title: "Eureka Mignon Zero Grinder (Chrome)", competitor: "The Kitchen Barista" },
  { idc_title: "Eureka Mignon Zero - Yellow", competitor_title: "Eureka Mignon Zero Grinder (Yellow)", competitor: "The Kitchen Barista" },
  { idc_title: "Eureka Mignon Zero - Red", competitor_title: "Eureka Mignon Zero Grinder (Red)", competitor: "The Kitchen Barista" },
  { idc_title: "Eureka Mignon Zero - Red", competitor_title: "Eureka Mignon Zero | Single Dose Coffee Grinder (Ferrari Red)", competitor: "HomeCoffeeSolutions.com" },
  { idc_title: "Eureka Mignon Libra 65 AP Grind by Weight - Silver", competitor_title: "Eureka Mignon Libra 65 AP Grinder with Grind by Weight (Chrome)", competitor: "The Kitchen Barista" }
];

// Continue with more batches...
console.log(`Total matches to create: ${matches.length}`);

// Generate SQL or API calls
console.log('\n-- SQL Insert statements --\n');

matches.forEach((match, index) => {
  console.log(`-- Match ${index + 1}: ${match.idc_title} -> ${match.competitor_title} (${match.competitor})`);
  console.log(`-- TODO: Need to look up actual IDs from database`);
});