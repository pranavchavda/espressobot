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
                <strong>Add Competitors:</strong> Configure competitor websites to scrape
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