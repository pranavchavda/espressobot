import { MCPServerStdio, MCPServerStreamableHttp } from '@openai/agents-core';
import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';
import chokidar from 'chokidar';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

class MCPServerManager {
  constructor() {
    this.servers = new Map();
    this.configPath = path.join(__dirname, '../../mcp-servers.json');
    this.watcher = null;
    this.builtInServers = new Map();
  }

  // Register built-in servers (like python-tools)
  registerBuiltInServer(name, server) {
    this.builtInServers.set(name, server);
  }

  async loadConfiguration() {
    try {
      const configData = await fs.readFile(this.configPath, 'utf8');
      const config = JSON.parse(configData);
      return config.mcpServers || {};
    } catch (error) {
      console.error('Error loading MCP configuration:', error);
      return {};
    }
  }

  async initializeServers() {
    const config = await this.loadConfiguration();
    
    console.log('[MCP Server Manager] Loading external MCP servers...');
    
    // Initialize external servers
    for (const [name, serverConfig] of Object.entries(config)) {
      if (serverConfig.enabled === false) {
        console.log(`[MCP Server Manager] Skipping disabled server: ${name}`);
        continue;
      }
      
      // Handle different server types
      if (serverConfig.type === 'http') {
        await this.createHTTPServer(name, serverConfig);
      } else if (!serverConfig.type || serverConfig.type === 'stdio') {
        await this.createStdioServer(name, serverConfig);
      } else {
        console.warn(`[MCP Server Manager] Unknown server type '${serverConfig.type}' for server: ${name}`);
      }
      
      // Handled above
    }

    // Add built-in servers
    console.log('[MCP Server Manager] Adding built-in servers...');
    for (const [name, server] of this.builtInServers.entries()) {
      this.servers.set(name, server);
      console.log(`  ✓ Built-in server: ${name}`);
    }
    
    console.log(`[MCP Server Manager] Total servers available: ${this.servers.size}`);
  }

  async createHTTPServer(name, config) {
    try {
      console.log(`[MCP Server Manager] Initializing HTTP MCP server: ${name}`);
      console.log(`  URL: ${config.url}`);
      
      const serverOptions = {
        name: config.description || name,
        url: config.url,
        cacheToolsList: true
      };

      // Add headers if specified
      if (config.headers) {
        serverOptions.requestInit = {
          headers: config.headers
        };
      }

      const server = new MCPServerStreamableHttp(serverOptions);
      await server.connect();
      
      this.servers.set(name, server);
      console.log(`✓ HTTP MCP server '${name}' connected successfully`);
      
      // List available tools
      try {
        const tools = await server.listTools();
        console.log(`  Available tools: ${tools.map(t => t.name).join(', ')}`);
      } catch (toolsError) {
        console.log(`  Could not list tools: ${toolsError.message}`);
      }
      
    } catch (error) {
      console.error(`Failed to initialize HTTP MCP server '${name}':`, error.message);
      if (error.stack) {
        console.error('Stack trace:', error.stack);
      }
    }
  }

  async createStdioServer(name, config) {
    try {
      console.log(`[MCP Server Manager] Initializing stdio MCP server: ${name}`);
      
      const serverOptions = {
        name: config.description || name,
        cacheToolsList: true
      };

      // Handle different command formats
      if (config.fullCommand) {
        serverOptions.fullCommand = config.fullCommand;
      } else {
        serverOptions.command = config.command;
        if (config.args) {
          serverOptions.args = config.args;
        }
      }

      // Add environment variables if specified
      if (config.env) {
        serverOptions.env = {
          ...process.env,
          ...config.env
        };
      }

      const server = new MCPServerStdio(serverOptions);
      await server.connect();
      
      this.servers.set(name, server);
      console.log(`✓ Stdio MCP server '${name}' connected successfully`);
      
      // List available tools
      const tools = await server.listTools();
      console.log(`  Available tools: ${tools.map(t => t.name).join(', ')}`);
      
    } catch (error) {
      console.error(`Failed to initialize stdio MCP server '${name}':`, error);
    }
  }

  async reloadServer(name, config) {
    // Disconnect existing server if it exists
    if (this.servers.has(name) && !this.builtInServers.has(name)) {
      const server = this.servers.get(name);
      await server.close();
      this.servers.delete(name);
    }

    // Reconnect if enabled
    if (config.enabled !== false) {
      // Handle different server types
      if (config.type === 'http') {
        await this.createHTTPServer(name, config);
      } else if (!config.type || config.type === 'stdio') {
        await this.createStdioServer(name, config);
      } else {
        console.warn(`[MCP Server Manager] Unknown server type '${config.type}' for server: ${name}`);
      }
    }
  }

  async watchConfiguration() {
    this.watcher = chokidar.watch(this.configPath, {
      persistent: true,
      ignoreInitial: true
    });

    this.watcher.on('change', async () => {
      console.log('MCP configuration changed, reloading...');
      const newConfig = await this.loadConfiguration();
      
      // Check for changes and reload affected servers
      const currentServerNames = new Set(this.servers.keys());
      const newServerNames = new Set(Object.keys(newConfig).filter(name => newConfig[name].enabled !== false));
      
      // Remove servers that are no longer in config or disabled
      for (const name of currentServerNames) {
        if (!this.builtInServers.has(name) && (!newServerNames.has(name) || newConfig[name]?.enabled === false)) {
          console.log(`Removing MCP server: ${name}`);
          const server = this.servers.get(name);
          await server.close();
          this.servers.delete(name);
        }
      }
      
      // Add or update servers
      for (const [name, config] of Object.entries(newConfig)) {
        if (config.enabled !== false) {
          await this.reloadServer(name, config);
        }
      }
    });
  }

  getAllServers() {
    return Array.from(this.servers.values());
  }

  getServer(name) {
    return this.servers.get(name);
  }

  getServerNames() {
    return Array.from(this.servers.keys());
  }

  async close() {
    if (this.watcher) {
      await this.watcher.close();
    }
    
    for (const [name, server] of this.servers.entries()) {
      if (!this.builtInServers.has(name)) {
        await server.close();
      }
    }
    
    this.servers.clear();
  }
}

export default MCPServerManager;