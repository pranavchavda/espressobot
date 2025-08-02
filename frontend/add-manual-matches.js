import fetch from 'node-fetch';
import fs from 'fs';

// Read the matches data
const matchesData = {
  "batch1": [
    {
      idc: { title: "Profitec RIDE Dual Boiler Espresso Machine", price: 3590 },
      competitors: [
        { name: "The Kitchen Barista", title: "Profitec RIDE Dual Boiler Espresso Machine", price: 3590 },
        { name: "Cafe Liegeois", title: "Profitec - RIDE Dual Boiler Espresso Machine", price: 3590 }
      ]
    },
    {
      idc: { title: "Profitec Twist A54 Espresso Grinder", price: 849 },
      competitors: [
        { name: "HomeCoffeeSolutions.com", title: "Profitec Twist A54 Coffee Grinder", price: 849 },
        { name: "Cafe Liegeois", title: "Profitec - Twist A54", price: 849 }
      ]
    },
    {
      idc: { title: "Profitec JUMP Espresso Machine", price: 2799 },
      competitors: [
        { name: "The Kitchen Barista", title: "Profitec Jump Espresso Machine", price: 2799 }
      ]
    },
    {
      idc: { title: "Profitec Pro 400 Espresso Machine - White", price: 2599 },
      competitors: [
        { name: "The Kitchen Barista", title: "Profitec Pro 400 Espresso Machine", price: 2599 },
        { name: "Cafe Liegeois", title: "Profitec - Pro 400 - Espresso Machine", price: 2599 }
      ]
    }
  ],
  "batch2": [
    {
      idc: { title: "Profitec Pro 400 Espresso Machine - Black", price: 2599 },
      competitors: [
        { name: "HomeCoffeeSolutions.com", title: "Profitec Pro 400 Heat Exchanger Espresso Machine With E61 Group Head & PID Temperature Control (Black)", price: 2599 }
      ]
    },
    {
      idc: { title: "Profitec Go Espresso Machine - Brushed Stainless Steel", price: 1599 },
      competitors: [
        { name: "HomeCoffeeSolutions.com", title: "Profitec Go Single Boiler PID Espresso Machine (Brushed Stainless Steel)", price: 1599 }
      ]
    },
    {
      idc: { title: "Profitec GO Espresso Machine - Blue", price: 1599 },
      competitors: [
        { name: "HomeCoffeeSolutions.com", title: "Profitec Go Single Boiler PID Espresso Machine (Blue)", price: 1599 }
      ]
    },
    {
      idc: { title: "Profitec Go Espresso Machine - Yellow", price: 1599 },
      competitors: [
        { name: "HomeCoffeeSolutions.com", title: "Profitec Go Single Boiler PID Espresso Machine (Yellow)", price: 1599 }
      ]
    }
  ],
  "batch3": [
    {
      idc: { title: "Profitec Go Espresso Machine - Red", price: 1599 },
      competitors: [
        { name: "HomeCoffeeSolutions.com", title: "Profitec Go Single Boiler PID Espresso Machine (Red)", price: 1599 },
        { name: "The Kitchen Barista", title: "Profitec Go Espresso Machine (Red)", price: 1599 }
      ]
    },
    {
      idc: { title: "Profitec Go Espresso Machine - Black", price: 1599 },
      competitors: [
        { name: "HomeCoffeeSolutions.com", title: "Profitec Go Single Boiler PID Espresso Machine (Black)", price: 1599 },
        { name: "The Kitchen Barista", title: "Profitec Go Espresso Machine (Black)", price: 1599 }
      ]
    },
    {
      idc: { title: "Profitec Milk Frothing Pitcher - 500 ml", price: 79.95 },
      competitors: [
        { name: "HomeCoffeeSolutions.com", title: "Profitec Milk Frothing Pitcher(500ml)", price: 79 }
      ]
    },
    {
      idc: { title: "Profitec Pro 400 Espresso Machine", price: 2599 },
      competitors: [
        { name: "HomeCoffeeSolutions.com", title: "Profitec Pro 400 Heat Exchanger Espresso Machine With E61 Group Head & PID Temperature Control (Black)", price: 2599 },
        { name: "The Kitchen Barista", title: "Profitec Pro 400 Espresso Machine", price: 2599 },
        { name: "Cafe Liegeois", title: "Profitec - Pro 400 - Espresso Machine", price: 2599 }
      ]
    },
    {
      idc: { title: "Profitec Pro 800 Espresso Machine", price: 4499 },
      competitors: [
        { name: "HomeCoffeeSolutions.com", title: "Profitec Pro 800 Lever Espresso Machine With PID Temperature Control", price: 4399 },
        { name: "The Kitchen Barista", title: "Profitec Pro 800 Lever Espresso Machine 2022 Version (Stainless Steel)", price: 4499 },
        { name: "Cafe Liegeois", title: "Profitec - Pro 800", price: 4499.99 }
      ]
    },
    {
      idc: { title: "Profitec Pro T64 Coffee Grinder", price: 1199 },
      competitors: [
        { name: "HomeCoffeeSolutions.com", title: "Profitec Pro T64 Coffee Grinder", price: 1199 },
        { name: "The Kitchen Barista", title: "Profitec Pro T64 Flat Burr Grinder (Stainless Steel)", price: 1119 },
        { name: "Cafe Liegeois", title: "Profitec - Pro T64 Grinder", price: 1199 }
      ]
    },
    {
      idc: { title: "Profitec Pro 500 Espresso Machine w/ Quick Steam", price: 2949 },
      competitors: [
        { name: "HomeCoffeeSolutions.com", title: "Profitec Pro 500 Heat Exchanger & Quick Steam Espresso Machine With E61 Group Head, PID Temperature Control", price: 2949 },
        { name: "The Kitchen Barista", title: "Profitec Pro 500 Espresso Machine w/ Quick Steam", price: 2949 }
      ]
    },
    {
      idc: { title: "Profitec Tamping Pad", price: 39 },
      competitors: [
        { name: "HomeCoffeeSolutions.com", title: "Profitec Tamping Pad", price: 39 },
        { name: "The Kitchen Barista", title: "Profitec Tamping Pad (Black)", price: 39 }
      ]
    },
    {
      idc: { title: "Profitec Pro 500 Espresso Machine w/ PID and Flow Control", price: 3049 },
      competitors: [
        { name: "HomeCoffeeSolutions.com", title: "Profitec Pro 500 Heat Exchanger Espresso Machine With E61 Group Head, PID Temperature Control, & Flow Control", price: 3049 },
        { name: "The Kitchen Barista", title: "Profitec Pro 500 Espresso Machine w/ PID and Flow Control", price: 3049 }
      ]
    },
    {
      idc: { title: "Profitec E61 Flow Control Device", price: 299 },
      competitors: [
        { name: "The Kitchen Barista", title: "Profitec E61 Flow Control Device", price: 295 }
      ]
    }
  ],
  "batch4": [
    {
      idc: { title: "Profitec Pro 500 Espresso Machine w/ PID", price: 2779 },
      competitors: [
        { name: "The Kitchen Barista", title: "Profitec Pro 500 Espresso Machine w/ PID", price: 2779 },
        { name: "HomeCoffeeSolutions.com", title: "Profitec Pro 500 Heat Exchanger Espresso Machine With E61 Group Head & PID Temperature Control", price: 2779 }
      ]
    },
    {
      idc: { title: "Eureka Mignon Zero - Blue", price: 599 },
      competitors: [
        { name: "HomeCoffeeSolutions.com", title: "Eureka Mignon Zero | Single Dose Coffee Grinder (Blue)", price: 599 }
      ]
    },
    {
      idc: { title: "Eureka Mignon Zero - Pale Blue", price: 599 },
      competitors: [
        { name: "The Kitchen Barista", title: "Eureka Mignon Zero Grinder (Pale Blue)", price: 589 }
      ]
    },
    {
      idc: { title: "Eureka Mignon Zero - Silver", price: 599 },
      competitors: [
        { name: "HomeCoffeeSolutions.com", title: "Eureka Mignon Zero | Single Dose Coffee Grinder (Chrome)", price: 599 },
        { name: "The Kitchen Barista", title: "Eureka Mignon Zero Grinder (Chrome)", price: 599 }
      ]
    },
    {
      idc: { title: "Eureka Mignon Zero - Yellow", price: 599 },
      competitors: [
        { name: "The Kitchen Barista", title: "Eureka Mignon Zero Grinder (Yellow)", price: 589 }
      ]
    },
    {
      idc: { title: "Eureka Mignon Zero - Red", price: 599 },
      competitors: [
        { name: "The Kitchen Barista", title: "Eureka Mignon Zero Grinder (Red)", price: 589 },
        { name: "HomeCoffeeSolutions.com", title: "Eureka Mignon Zero | Single Dose Coffee Grinder (Ferrari Red)", price: 599 }
      ]
    },
    {
      idc: { title: "Eureka Mignon Libra 65 AP Grind by Weight - Silver", price: 1299 },
      competitors: [
        { name: "The Kitchen Barista", title: "Eureka Mignon Libra 65 AP Grinder with Grind by Weight (Chrome)", price: 1349 }
      ]
    }
  ]
};

// Load all products to get IDs
const idcProducts = JSON.parse(fs.readFileSync('all_idc_products.csv', 'utf8'));
const competitorProducts = JSON.parse(fs.readFileSync('all_competitor_products.csv', 'utf8'));

// Create a lookup map
const idcMap = {};
const competitorMap = {};

// Parse CSV data
// For now, let me just output the matches in a format ready for manual entry

console.log('Manual Matches to Create:');
console.log('========================\n');

let matchCount = 0;

Object.entries(matchesData).forEach(([batch, products]) => {
  console.log(`\n${batch.toUpperCase()}:`);
  products.forEach(match => {
    console.log(`\nIDC Product: ${match.idc.title} ($${match.idc.price})`);
    match.competitors.forEach(comp => {
      matchCount++;
      console.log(`  → ${comp.name}: ${comp.title} ($${comp.price})`);
    });
  });
});

console.log(`\n\nTotal Matches to Create: ${matchCount}`);