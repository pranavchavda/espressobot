import React from 'react';
import { Badge } from "@common/badge";

function AboutPage() {
  return (
    <div className="container mx-auto p-6 max-w-4xl">
      <h1 className="text-3xl font-bold mb-6 text-zinc-800 dark:text-zinc-200">About EspressoBot</h1>
      
      <div className="prose dark:prose-invert max-w-none">
        <p className="text-lg mb-6">
          EspressoBot is a next-generation AI assistant for iDrinkCoffee.com, built to accelerate your workflow and boost customer support using advanced tools, APIs, and intelligent automation. Now featuring streaming chat, image understanding, Google sign-in, user-specific chat histories, and more. Here's how EspressoBot empowers you:
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
              <li>Experience token-by-token streaming for a natural conversation flow, similar to ChatGPT.</li>
            </ul>
          </section>
          
          <section>
            <h2 className="text-2xl font-semibold mb-3 text-indigo-600 dark:text-indigo-400">🧠 Advanced AI Capabilities</h2>
            <ul className="list-disc pl-5 space-y-2">
              <li>Access Perplexity AI for real-time research on e-commerce trends, products, and competitors.</li>
              <li>Utilize structured step-by-step reasoning for complex problem-solving via Sequential Thinking.</li>
              <li>Benefit from persistent memory that remembers your preferences and previous interactions.</li>
              <li>Get web content fetched and analyzed directly through our Fetch integration.</li>
              <li><b>Understand and analyze images:</b> Upload product photos, screenshots, or diagrams for instant insights and suggestions.</li>
              <li><b>Shell Agency Architecture:</b> Dynamic bash orchestrator with specialized agents for task planning, software engineering, and semantic operations.</li>
              <li><b>MCP Integration:</b> Direct tool execution with Python Tools MCP Server and Shopify Dev documentation access.</li>
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
              <li className="bg-white dark:bg-zinc-800 p-3 rounded border border-blue-200 dark:border-blue-800">
                <span className="font-mono text-sm text-blue-600 dark:text-blue-300">"Use Sequential Thinking to analyze our sales trends for the past quarter and suggest inventory adjustments."</span>
              </li>
              <li className="bg-white dark:bg-zinc-800 p-3 rounded border border-blue-200 dark:border-blue-800">
                <span className="font-mono text-sm text-blue-600 dark:text-blue-300">"Fetch the latest reviews for the ECM Synchronika from Home-Barista forums and summarize the key points."</span>
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
              <li>For complex analyses, explicitly mention "Sequential Thinking" to activate structured reasoning.</li>
              <li>When researching external information, specify "Search Perplexity" for up-to-date results.</li>
            </ul>
          </section>
          
          <section className="bg-green-50 dark:bg-green-900/30 p-4 rounded-lg mt-8">
            <h3 className="text-lg font-semibold mb-2 text-green-700 dark:text-green-300">✨ New Features & Integrations</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-white dark:bg-zinc-800 p-4 rounded border border-green-200 dark:border-green-800">
                <h4 className="font-medium text-green-600 dark:text-green-400">Vision</h4>
                <p className="text-sm mt-1">Analyze images, screenshots, and product photos for instant insights and suggestions.</p>
              </div>
              <div className="bg-white dark:bg-zinc-800 p-4 rounded border border-green-200 dark:border-green-800">
                <h4 className="font-medium text-green-600 dark:text-green-400">Streaming Chat</h4>
                <p className="text-sm mt-1">Enjoy real-time, token-by-token chat responses for a natural and interactive experience.</p>
              </div>
              <div className="bg-white dark:bg-zinc-800 p-4 rounded border border-green-200 dark:border-green-800">
                <h4 className="font-medium text-green-600 dark:text-green-400">Title Creator</h4>
                <p className="text-sm mt-1">Automatically generates concise titles for your conversations in the sidebar.</p>
              </div>
              <div className="bg-white dark:bg-zinc-800 p-4 rounded border border-green-200 dark:border-green-800">
                <h4 className="font-medium text-green-600 dark:text-green-400">Planner Agent</h4>
                <p className="text-sm mt-1">Outlines a clear sequence of steps for complex tasks and visualizes them as a task plan.</p>
              </div>
              <div className="bg-white dark:bg-zinc-800 p-4 rounded border border-green-200 dark:border-green-800">
                <h4 className="font-medium text-green-600 dark:text-green-400">Shell Agency Mode</h4>
                <p className="text-sm mt-1">Unix-philosophy based architecture with bash orchestrator, dynamic agent spawning, and direct tool execution for maximum flexibility.</p>
              </div>
              <div className="bg-white dark:bg-zinc-800 p-4 rounded border border-green-200 dark:border-green-800">
                <h4 className="font-medium text-green-600 dark:text-green-400">User Authentication</h4>
                <p className="text-sm mt-1">Sign in securely with Google. Only approved (whitelisted) team members can access the platform. Each user sees only their own chats.</p>
              </div>
              <div className="bg-white dark:bg-zinc-800 p-4 rounded border border-green-200 dark:border-green-800">
                <h4 className="font-medium text-green-600 dark:text-green-400">Google Tasks</h4>
                <p className="text-sm mt-1">Fetch, create, and manage your Google Tasks directly from chat <Badge color="blue\">coming soon</Badge>.</p>
              </div>
              <div className="bg-white dark:bg-zinc-800 p-4 rounded border border-green-200 dark:border-green-800">
                <h4 className="font-medium text-green-600 dark:text-green-400">MCP Servers</h4>
                <p className="text-sm mt-1">Python Tools MCP for direct tool execution, Shopify Dev MCP for API docs, and support for external MCP servers via JSON configuration.</p>
              </div>
              <div className="bg-white dark:bg-zinc-800 p-4 rounded border border-green-200 dark:border-green-800">
                <h4 className="font-medium text-green-600 dark:text-green-400">Perplexity</h4>
                <p className="text-sm mt-1">Get real-time research and information from Perplexity AI's powerful knowledge engine.</p>
              </div>
              <div className="bg-white dark:bg-zinc-800 p-4 rounded border border-green-200 dark:border-green-800">
                <h4 className="font-medium text-green-600 dark:text-green-400">Fetch</h4>
                <p className="text-sm mt-1">Retrieve and analyze web content from various sources to support your decision-making.</p>
              </div>
              <div className="bg-white dark:bg-zinc-800 p-4 rounded border border-green-200 dark:border-green-800">
                <h4 className="font-medium text-green-600 dark:text-green-400">Sequential Thinking</h4>
                <p className="text-sm mt-1">Solve complex problems with structured step-by-step reasoning for better analytical results.</p>
              </div>
              <div className="bg-white dark:bg-zinc-800 p-4 rounded border border-green-200 dark:border-green-800">
                <h4 className="font-medium text-green-600 dark:text-green-400">Local Memory System</h4>
                <p className="text-sm mt-1">SQLite-based semantic memory with OpenAI embeddings, deduplication, and user isolation for unlimited operations.</p>
              </div>
              <div className="bg-white dark:bg-zinc-800 p-4 rounded border border-green-200 dark:border-green-800">
                <h4 className="font-medium text-green-600 dark:text-green-400">Filesystem</h4>
                <p className="text-sm mt-1">Secure file operations for managing documents and data within designated directories.</p>
              </div>
              <div className="bg-white dark:bg-zinc-800 p-4 rounded border border-green-200 dark:border-green-800">
                <h4 className="font-medium text-green-600 dark:text-green-400">Task System</h4>
                <p className="text-sm mt-1">Persistent TODO management with file-based storage that survives restarts and tracks multi-step operations.</p>
              </div>
              <div className="bg-white dark:bg-zinc-800 p-4 rounded border border-green-200 dark:border-green-800">
                <h4 className="font-medium text-green-600 dark:text-green-400">Dynamic Tool Creation</h4>
                <p className="text-sm mt-1">Agents can create and compose tools on the fly using bash, enabling rapid prototyping and custom solutions.</p>
              </div>
              <div className="bg-white dark:bg-zinc-800 p-4 rounded border border-green-200 dark:border-green-800">
                <h4 className="font-medium text-green-600 dark:text-green-400">External MCP Servers</h4>
                <p className="text-sm mt-1">Add custom MCP servers via JSON config with hot reload. Compatible with Claude Desktop format for easy integration.</p>
              </div>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}

export default AboutPage;
