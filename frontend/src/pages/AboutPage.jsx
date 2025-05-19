import React from 'react';
import { Badge } from "@common/badge";

function AboutPage() {
  return (
    <div className="container mx-auto p-6 max-w-4xl">
      <h1 className="text-3xl font-bold mb-6 text-zinc-800 dark:text-zinc-200">About EspressoBot</h1>
      
      <div className="prose dark:prose-invert max-w-none">
        <p className="text-lg mb-6">
          EspressoBot is the specialized AI-powered assistant created for the iDrinkCoffee.com team, designed to streamline daily operations and enhance customer support by leveraging various tools and APIs. Here's how EspressoBot can empower you:
        </p>

        <div className="space-y-8">
          <section>
            <h2 className="text-2xl font-semibold mb-3 text-indigo-600 dark:text-indigo-400">🛍️ Shopify Store & Customer Management</h2>
            <ul className="list-disc pl-5 space-y-2">
              <li>Quickly fetch product details: "What are the specifications for the ECM Synchronika II?" or "Show me Eureka Grinders under $500."</li>
              <li>Access order information: "Find John Doe's recent order for a Eureka Mignon Specialita." or "What's the shipping status for order #12345?"</li>
              <li>Retrieve customer data: "Show purchase history for jane.doe@example.com." or "Has this customer previously purchased a bottomless portafilter?"</li>
              <li>Manage products: "Update 'Daterra Farms Espresso Yellow' to allow overselling."</li>
              <li>Create promotions: "Generate a 10% discount code for all 'Accessory' collection items, valid for this weekend."</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-3 text-indigo-600 dark:text-indigo-400">📦 SkuVault Inventory & Product Sync</h2>
            <ul className="list-disc pl-5 space-y-2">
              <li>Upload new products: "Add the new 'White Bird Coffee Scale' to Shopify and SkuVault using these details..."</li>
              <li>Update inventory: "Update the stock level for 'Daterra Farms Espresso Yellow' product to 50 units."</li>

                <Badge color="blue">
                  coming soon
                </Badge>
            </ul>
          </section>
          
          <section>
            <h2 className="text-2xl font-semibold mb-3 text-indigo-600 dark:text-indigo-400">💬 Efficient AI-Powered Assistance</h2>
            <ul className="list-disc pl-5 space-y-2">
              <li>Get immediate, streaming responses to your operational queries, helping you assist customers faster.</li>
              <li>Let EspressoBot handle complex data lookups or multi-step tasks across Shopify and SkuVault.</li>
              <li>Use natural language for requests, making your workflow smoother and more intuitive.</li>
            </ul>
          </section>

          <section className="bg-blue-50 dark:bg-blue-900/30 p-4 rounded-lg">
            <h3 className="text-lg font-semibold mb-2 text-blue-700 dark:text-blue-300">🚀 Example Interactions for iDrinkCoffee.com Staff</h3>
            <ul className="space-y-2">
              <li className="bg-white dark:bg-zinc-800 p-3 rounded border border-blue-200 dark:border-blue-800">
                <span className="font-mono text-sm text-blue-600 dark:text-blue-300">"List all open orders for 'La Marzocco Linea Mini R'."</span>
              </li>
              <li className="bg-white dark:bg-zinc-800 p-3 rounded border border-blue-200 dark:border-blue-800">
                <span className="font-mono text-sm text-blue-600 dark:text-blue-300">"Update SkuVault inventory for SKU 'FEL-ODE-BLK-G2' to 50 units."</span>
              </li>
              <li className="bg-white dark:bg-zinc-800 p-3 rounded border border-blue-200 dark:border-blue-800">
                <span className="font-mono text-sm text-blue-600 dark:text-blue-300">"Customer is asking for grinders under $500 suitable for espresso. What do we have in stock?"</span>
              </li>
              <li className="bg-white dark:bg-zinc-800 p-3 rounded border border-blue-200 dark:border-blue-800">
                <span className="font-mono text-sm text-blue-600 dark:text-blue-300">"Create a Shopify product: 'Seasonal Coffee Bean Example'. Set price to $24.99, cost $12. SKU 'IDC-SEASONAL-COFFEE-BEAN'. Upload image from [link]. More info available at [link]."</span>
              </li>
               <li className="bg-white dark:bg-zinc-800 p-3 rounded border border-blue-200 dark:border-blue-800">
                <span className="font-mono text-sm text-blue-600 dark:text-blue-300">"Search Perplexity for reviews comparing the 'Eureka Mignon Specialita' and the 'Niche Zero'."</span>
              </li>
            </ul>
          </section>
          
          <section>
            <h2 className="text-2xl font-semibold mb-3 text-indigo-600 dark:text-indigo-400">💡 Tips for Best Results at iDrinkCoffee.com</h2>
            <ul className="list-disc pl-5 space-y-2">
              <li>When inquiring about products, use specific names (e.g., "Coffee Brain Genesis Super Automatic Espresso Machine") or SKUs if known.</li>
              <li>For customer-related queries, provide order numbers or email addresses for faster lookups.</li>
              <li>If a task involves multiple steps (e.g., creating a product and then adding it to a collection), break it down or clearly state the full intent.</li>
              <li>Ensure your API credentials for Shopify and SkuVault are active and correctly configured.</li>
            </ul>
          </section>
        </div>
      </div>
    </div>
  );
}

export default AboutPage;
