import React from 'react';
import { Heading } from '@common/heading';
import { Badge } from '@common/badge';

export default function PriceMonitorHelp() {
  return (
    <div className="p-4 md:p-6 max-w-4xl mx-auto">
      <div className="mb-8">
        <Heading level="1">Price Monitor Help</Heading>
        <p className="mt-2 text-gray-600 dark:text-gray-400">
          Complete guide to using the MAP (Minimum Advertised Price) enforcement system
        </p>
      </div>

      <div className="space-y-8">
        {/* Quick Start */}
        <section className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
          <h2 className="text-xl font-semibold mb-4 flex items-center">
            🚀 Quick Start Guide
          </h2>
          <div className="space-y-3">
            <div className="flex items-start gap-3">
              <Badge color="blue">1</Badge>
              <div>
                <strong>Sync Shopify Products:</strong> Import your products from Shopify to start monitoring
              </div>
            </div>
            <div className="flex items-start gap-3">
              <Badge color="blue">2</Badge>
              <div>
                <strong>Add Competitors:</strong> Configure competitor websites with flexible scraping strategies (collections, URL patterns, or search terms)
              </div>
            </div>
            <div className="flex items-start gap-3">
              <Badge color="blue">3</Badge>
              <div>
                <strong>Run Scraping:</strong> Collect competitor product data and pricing
              </div>
            </div>
            <div className="flex items-start gap-3">
              <Badge color="blue">4</Badge>
              <div>
                <strong>Match Products:</strong> Use AI to match your products with competitor products
              </div>
            </div>
            <div className="flex items-start gap-3">
              <Badge color="blue">5</Badge>
              <div>
                <strong>Scan Violations:</strong> Detect MAP violations and take action
              </div>
            </div>
          </div>
        </section>

        {/* Competitor Scraping Strategies */}
        <section className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
          <h2 className="text-xl font-semibold mb-4 flex items-center">
            🌐 Competitor Scraping Strategies
          </h2>
          <p className="text-gray-600 dark:text-gray-400 text-sm mb-6">
            Configure how to find products on different competitor websites using flexible scraping strategies.
          </p>
          
          <div className="space-y-6">
            {/* Collection-based Strategy */}
            <div className="border border-gray-200 dark:border-gray-600 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-3">
                <Badge color="blue">Collections</Badge>
                <h3 className="font-medium">Collection-based Scraping</h3>
              </div>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
                Best for traditional Shopify stores that organize products into collections.
              </p>
              <div className="bg-gray-50 dark:bg-gray-700 p-3 rounded-lg mb-3">
                <code className="text-sm">Collections: ecm, profitec, eureka</code>
              </div>
              <div className="space-y-2">
                <div className="text-sm">
                  <strong>Example URLs:</strong>
                  <ul className="ml-4 mt-1 space-y-1 text-gray-600 dark:text-gray-400">
                    <li>• https://homecoffeesolutions.com/collections/ecm</li>
                    <li>• https://homecoffeesolutions.com/collections/profitec</li>
                    <li>• https://homecoffeesolutions.com/collections/eureka</li>
                  </ul>
                </div>
                <div className="text-sm">
                  <strong>Use when:</strong> Competitor uses standard /collections/[name] URL structure
                </div>
              </div>
            </div>

            {/* URL Pattern Strategy */}
            <div className="border border-gray-200 dark:border-gray-600 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-3">
                <Badge color="green">URL Patterns</Badge>
                <h3 className="font-medium">URL Pattern Matching</h3>
              </div>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
                Perfect for sites without collections - match products by URL patterns with wildcards.
              </p>
              <div className="bg-gray-50 dark:bg-gray-700 p-3 rounded-lg mb-3">
                <code className="text-sm whitespace-pre-line">{`/products/ecm-*
/products/profitec-*
/products/*espresso*
/products/*grinder*`}</code>
              </div>
              <div className="space-y-2">
                <div className="text-sm">
                  <strong>Example for thekitchenbarista.com:</strong>
                  <ul className="ml-4 mt-1 space-y-1 text-gray-600 dark:text-gray-400">
                    <li>• /products/ecm-* matches all ECM machine URLs</li>
                    <li>• /products/*espresso* matches any URL containing "espresso"</li>
                    <li>• /products/*grinder* matches any URL containing "grinder"</li>
                  </ul>
                </div>
                <div className="text-sm">
                  <strong>Use when:</strong> Competitor has predictable URL patterns but no collections
                </div>
              </div>
            </div>

            {/* Search Terms Strategy */}
            <div className="border border-gray-200 dark:border-gray-600 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-3">
                <Badge color="orange">Search Terms</Badge>
                <h3 className="font-medium">Search Term Based (Most Comprehensive)</h3>
              </div>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
                Most flexible strategy - tries multiple approaches to find products by search terms.
              </p>
              <div className="bg-gray-50 dark:bg-gray-700 p-3 rounded-lg mb-3">
                <code className="text-sm">ECM, Profitec, Eureka, espresso machine, burr grinder</code>
              </div>
              <div className="space-y-2">
                <div className="text-sm">
                  <strong>Three-tier search approach:</strong>
                  <ul className="ml-4 mt-1 space-y-1 text-gray-600 dark:text-gray-400">
                    <li>• <strong>1. Shopify Search API:</strong> Uses site's built-in search if available</li>
                    <li>• <strong>2. Collection Inference:</strong> Converts terms to potential collection names</li>
                    <li>• <strong>3. Full Crawl & Filter:</strong> Searches all products by title/vendor/tags</li>
                  </ul>
                </div>
                <div className="text-sm">
                  <strong>Smart variations tried:</strong>
                  <ul className="ml-4 mt-1 space-y-1 text-gray-600 dark:text-gray-400">
                    <li>• "ECM" → tries: ecm, ecm-espresso, ecm-machines, ecm-grinders</li>
                    <li>• "espresso machine" → tries: espresso-machine, espresso, espressomachine</li>
                  </ul>
                </div>
                <div className="text-sm">
                  <strong>Best for:</strong> Any site structure, maximum product discovery, comprehensive coverage
                </div>
              </div>
            </div>

            {/* Exclude Patterns */}
            <div className="border border-gray-200 dark:border-gray-600 rounded-lg p-4 bg-yellow-50 dark:bg-yellow-900/20">
              <div className="flex items-center gap-2 mb-3">
                <Badge color="red">Exclude</Badge>
                <h3 className="font-medium">Exclude Patterns (Universal)</h3>
              </div>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
                Available for all strategies - exclude unwanted products like clearance items.
              </p>
              <div className="bg-gray-50 dark:bg-gray-700 p-3 rounded-lg mb-3">
                <code className="text-sm whitespace-pre-line">{`*clearance*
*sale*
*discontinued*
*refurbished*
*open-box*`}</code>
              </div>
              <div className="text-sm">
                <strong>Common exclusions:</strong>
                <ul className="ml-4 mt-1 space-y-1 text-gray-600 dark:text-gray-400">
                  <li>• Sale and clearance items (often below MAP intentionally)</li>
                  <li>• Discontinued products</li>
                  <li>• Refurbished or open-box items</li>
                  <li>• Demo units and display models</li>
                </ul>
              </div>
            </div>
          </div>

          <div className="mt-6 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
            <h4 className="font-medium text-blue-900 dark:text-blue-100 mb-2">💡 Strategy Selection Guide:</h4>
            <ul className="text-sm text-blue-800 dark:text-blue-200 space-y-1">
              <li>• <strong>Collections:</strong> ⚡ Fastest for standard Shopify sites with known collections</li>
              <li>• <strong>URL Patterns:</strong> 🎯 Best for predictable URLs but unknown collection names</li>
              <li>• <strong>Search Terms:</strong> 🔍 Most comprehensive - tries API, collections, and full crawl</li>
              <li>• <strong>When unsure:</strong> Start with search terms strategy for maximum coverage</li>
              <li>• <strong>For performance:</strong> Use collections if you know the exact names</li>
              <li>• <strong>For discovery:</strong> Use search terms to find products you might miss otherwise</li>
            </ul>
          </div>
        </section>

        {/* Dashboard */}
        <section className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
          <h2 className="text-xl font-semibold mb-4 flex items-center">
            📊 Dashboard Overview
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
              <h3 className="font-medium text-blue-900 dark:text-blue-100">IDC Products</h3>
              <p className="text-sm text-blue-700 dark:text-blue-300">Your monitored products from Shopify</p>
            </div>
            <div className="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg">
              <h3 className="font-medium text-green-900 dark:text-green-100">Competitor Products</h3>
              <p className="text-sm text-green-700 dark:text-green-300">Products scraped from competitor sites</p>
            </div>
            <div className="p-4 bg-orange-50 dark:bg-orange-900/20 rounded-lg">
              <h3 className="font-medium text-orange-900 dark:text-orange-100">Product Matches</h3>
              <p className="text-sm text-orange-700 dark:text-orange-300">AI-powered matches between your products and competitors</p>
            </div>
            <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-lg">
              <h3 className="font-medium text-red-900 dark:text-red-100">Active Violations</h3>
              <p className="text-sm text-red-700 dark:text-red-300">MAP violations requiring attention</p>
            </div>
          </div>
        </section>

        {/* Product Matching */}
        <section className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
          <h2 className="text-xl font-semibold mb-4 flex items-center">
            🤖 Product Matching
          </h2>
          <div className="space-y-4">
            <div>
              <h3 className="font-medium mb-2">Automatic Matching</h3>
              <p className="text-gray-600 dark:text-gray-400 text-sm mb-2">
                Uses AI with hybrid scoring: 40% semantic similarity + 60% traditional factors (brand, title, price, type).
              </p>
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <Badge color="green">High</Badge>
                  <span className="text-sm">80%+ confidence - Very likely matches</span>
                </div>
                <div className="flex items-center gap-2">
                  <Badge color="yellow">Medium</Badge>
                  <span className="text-sm">70-79% confidence - Possible matches</span>
                </div>
                <div className="flex items-center gap-2">
                  <Badge color="gray">Low</Badge>
                  <span className="text-sm">60-69% confidence - Weak matches</span>
                </div>
              </div>
            </div>
            
            <div>
              <h3 className="font-medium mb-2">Manual Matching</h3>
              <p className="text-gray-600 dark:text-gray-400 text-sm">
                Create custom matches when automatic matching isn't perfect. Use the "Create Manual Match" button to pair specific products.
              </p>
            </div>
          </div>
        </section>

        {/* MAP Violations */}
        <section className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
          <h2 className="text-xl font-semibold mb-4 flex items-center">
            ⚠️ MAP Violation Detection
          </h2>
          <div className="space-y-4">
            <p className="text-gray-600 dark:text-gray-400 text-sm">
              MAP violations occur when competitors sell below your minimum advertised price.
            </p>
            
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Badge color="red">Severe</Badge>
                <span className="text-sm">20%+ below MAP - Immediate attention required</span>
              </div>
              <div className="flex items-center gap-2">
                <Badge color="yellow">Moderate</Badge>
                <span className="text-sm">10-19% below MAP - Monitor closely</span>
              </div>
              <div className="flex items-center gap-2">
                <Badge color="orange">Minor</Badge>
                <span className="text-sm">5-9% below MAP - Consider action</span>
              </div>
            </div>

            <div className="bg-yellow-50 dark:bg-yellow-900/20 p-4 rounded-lg">
              <h4 className="font-medium text-yellow-900 dark:text-yellow-100 mb-2">Important Notes:</h4>
              <ul className="text-sm text-yellow-800 dark:text-yellow-200 space-y-1">
                <li>• Violations are detected from matched products only</li>
                <li>• Run "Scan Violations" after creating new matches</li>
                <li>• False positives can occur with poor matches - verify manually</li>
                <li>• Focus on high-confidence matches for accurate violation detection</li>
              </ul>
            </div>
          </div>
        </section>

        {/* Best Practices */}
        <section className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
          <h2 className="text-xl font-semibold mb-4 flex items-center">
            💡 Best Practices
          </h2>
          <div className="space-y-4">
            <div>
              <h3 className="font-medium mb-2">Data Quality</h3>
              <ul className="text-sm text-gray-600 dark:text-gray-400 space-y-1">
                <li>• Ensure product titles are descriptive and consistent</li>
                <li>• Keep pricing updated in Shopify</li>
                <li>• Review and delete poor quality matches</li>
                <li>• Use manual matching for critical products</li>
              </ul>
            </div>
            
            <div>
              <h3 className="font-medium mb-2">Monitoring Workflow</h3>
              <ul className="text-sm text-gray-600 dark:text-gray-400 space-y-1">
                <li>• Run scraping weekly or bi-weekly</li>
                <li>• Review new matches before scanning violations</li>
                <li>• Focus on severe violations first</li>
                <li>• Keep records of enforcement actions taken</li>
              </ul>
            </div>
          </div>
        </section>

        {/* Troubleshooting */}
        <section className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
          <h2 className="text-xl font-semibold mb-4 flex items-center">
            🔧 Troubleshooting
          </h2>
          <div className="space-y-4">
            <div>
              <h3 className="font-medium mb-2">No Matches Found</h3>
              <ul className="text-sm text-gray-600 dark:text-gray-400 space-y-1">
                <li>• Check if competitor products were scraped successfully</li>
                <li>• Lower the confidence threshold to "Low" temporarily</li>
                <li>• Use manual matching for difficult products</li>
                <li>• Ensure product titles are descriptive</li>
              </ul>
            </div>
            
            <div>
              <h3 className="font-medium mb-2">Poor Match Quality</h3>
              <ul className="text-sm text-gray-600 dark:text-gray-400 space-y-1">
                <li>• Delete incorrect matches individually</li>
                <li>• Focus on high-confidence matches only</li>
                <li>• Use manual matching for important products</li>
                <li>• Check that competitor data is accurate</li>
              </ul>
            </div>
            
            <div>
              <h3 className="font-medium mb-2">No Violations Detected</h3>
              <ul className="text-sm text-gray-600 dark:text-gray-400 space-y-1">
                <li>• Verify that matches exist before scanning</li>
                <li>• Check that competitor prices are below your prices</li>
                <li>• Run "Scan Violations" manually after creating matches</li>
                <li>• Review violation severity thresholds</li>
              </ul>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}