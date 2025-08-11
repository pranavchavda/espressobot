import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Heading } from '@common/heading';
import { Button } from '@common/button';
import { Text } from '@common/text';
import { Input } from '@common/input';
import { Textarea } from '@common/textarea';
import { Select } from '@common/select';
import { Badge } from '@common/badge';
import { Dialog, DialogActions, DialogDescription, DialogTitle } from '@common/dialog';
import { 
  Plus,
  X,
  Server,
  Terminal,
  Globe,
  Wifi,
  Activity,
  Upload,
  Share2,
  RefreshCw,
  Edit2,
  Trash2,
  PlayCircle,
  CheckCircle,
  XCircle,
  AlertCircle,
  ChevronLeft,
  Code,
  Lock,
  Unlock
} from 'lucide-react';

const MCPServerManager = () => {
  const navigate = useNavigate();
  const [servers, setServers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('my-servers');
  const [selectedServer, setSelectedServer] = useState(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [testDialogOpen, setTestDialogOpen] = useState(false);
  const [importDialogOpen, setImportDialogOpen] = useState(false);
  const [testResults, setTestResults] = useState(null);
  const [testing, setTesting] = useState(false);
  const [marketplace, setMarketplace] = useState([]);

  // Form state for new/edit server
  const [serverForm, setServerForm] = useState({
    name: '',
    display_name: '',
    description: '',
    server_type: 'stdio',
    connection_config: {},
    requires_auth: false,
    auth_config: null,
    rate_limit: null
  });

  // Server type icons
  const getServerIcon = (type) => {
    switch (type) {
      case 'stdio': return <Terminal className="h-5 w-5" />;
      case 'http': return <Globe className="h-5 w-5" />;
      case 'sse': return <Activity className="h-5 w-5" />;
      case 'websocket': return <Wifi className="h-5 w-5" />;
      default: return <Server className="h-5 w-5" />;
    }
  };

  // Status colors
  const getStatusBadge = (status) => {
    switch (status) {
      case 'connected': return <Badge color="green">Connected</Badge>;
      case 'failed': return <Badge color="red">Failed</Badge>;
      case 'testing': return <Badge color="yellow">Testing</Badge>;
      case 'disabled': return <Badge color="zinc">Disabled</Badge>;
      default: return <Badge color="blue">Pending</Badge>;
    }
  };

  useEffect(() => {
    loadServers();
    loadMarketplace();
  }, []);

  const loadServers = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/user-mcp-servers');
      const data = await response.json();
      setServers(data);
    } catch (error) {
      console.error('Failed to load servers:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadMarketplace = async () => {
    try {
      const response = await fetch('/api/user-mcp-servers/marketplace/popular');
      const data = await response.json();
      setMarketplace(data);
    } catch (error) {
      console.error('Failed to load marketplace:', error);
    }
  };

  const handleAddServer = () => {
    setServerForm({
      name: '',
      display_name: '',
      description: '',
      server_type: 'stdio',
      connection_config: {
        command: '',
        args: [],
        env: {}
      },
      requires_auth: false,
      auth_config: null,
      rate_limit: null
    });
    setDialogOpen(true);
  };

  const handleEditServer = async (serverId) => {
    try {
      const response = await fetch(`/api/user-mcp-servers/${serverId}`);
      const server = await response.json();
      
      // Ensure connection_config is properly formatted
      if (!server.connection_config || typeof server.connection_config !== 'object') {
        // Initialize based on server type
        switch (server.server_type) {
          case 'stdio':
            server.connection_config = { command: '', args: [], env: {} };
            break;
          case 'http':
            server.connection_config = { base_url: '' };
            break;
          case 'sse':
            server.connection_config = { url: '', headers: {} };
            break;
          case 'websocket':
            server.connection_config = { url: '' };
            break;
          default:
            server.connection_config = {};
        }
      }
      
      setServerForm(server);
      setDialogOpen(true);
    } catch (error) {
      console.error('Failed to load server details:', error);
    }
  };

  const handleTestServer = async () => {
    setTesting(true);
    setTestResults(null);
    
    try {
      const response = await fetch('/api/user-mcp-servers/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          server_type: serverForm.server_type,
          connection_config: serverForm.connection_config,
          auth_config: serverForm.auth_config
        })
      });
      
      const result = await response.json();
      setTestResults(result);
      
      if (result.success) {
        setTestDialogOpen(true);
      }
    } catch (error) {
      setTestResults({
        success: false,
        error: error.message
      });
    } finally {
      setTesting(false);
    }
  };

  const handleSaveServer = async () => {
    try {
      // Ensure connection_config is properly formatted
      const formData = {
        ...serverForm,
        connection_config: serverForm.connection_config || {}
      };
      
      // Validate required fields based on server type
      if (serverForm.server_type === 'stdio' && !serverForm.connection_config.command) {
        alert('Command is required for STDIO server type');
        return;
      }
      if (serverForm.server_type === 'http' && !serverForm.connection_config.base_url) {
        alert('Base URL is required for HTTP server type');
        return;
      }
      if ((serverForm.server_type === 'sse' || serverForm.server_type === 'websocket') && !serverForm.connection_config.url) {
        alert('URL is required for ' + serverForm.server_type.toUpperCase() + ' server type');
        return;
      }
      
      const method = serverForm.id ? 'PUT' : 'POST';
      const url = serverForm.id 
        ? `/api/user-mcp-servers/${serverForm.id}`
        : '/api/user-mcp-servers';
      
      const response = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });
      
      if (response.ok) {
        await loadServers();
        setDialogOpen(false);
      } else {
        const error = await response.json();
        console.error('Server save error:', error);
        alert(`Error: ${error.detail || 'Failed to save server'}`);
      }
    } catch (error) {
      console.error('Failed to save server:', error);
      alert(`Failed to save server: ${error.message}`);
    }
  };

  const handleDeleteServer = async (serverId) => {
    if (!confirm('Are you sure you want to delete this server?')) return;
    
    try {
      const response = await fetch(`/api/user-mcp-servers/${serverId}`, {
        method: 'DELETE'
      });
      
      if (response.ok) {
        await loadServers();
      }
    } catch (error) {
      console.error('Failed to delete server:', error);
    }
  };

  const handleImportClaude = async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      const response = await fetch('/api/user-mcp-servers/import-claude', {
        method: 'POST',
        body: formData
      });
      
      const result = await response.json();
      alert(`Imported ${result.imported.length} servers, ${result.failed.length} failed`);
      await loadServers();
      setImportDialogOpen(false);
    } catch (error) {
      alert(`Import failed: ${error.message}`);
    }
  };

  const renderConnectionConfig = () => {
    switch (serverForm.server_type) {
      case 'stdio':
        return (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">Command</label>
              <Input
                value={serverForm.connection_config.command || ''}
                onChange={(e) => setServerForm(prev => ({
                  ...prev,
                  connection_config: {
                    ...prev.connection_config,
                    command: e.target.value
                  }
                }))}
                placeholder="e.g., python, node, npx"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Arguments (comma-separated)</label>
              <Input
                value={(serverForm.connection_config.args || []).join(', ')}
                onChange={(e) => setServerForm(prev => ({
                  ...prev,
                  connection_config: {
                    ...prev.connection_config,
                    args: e.target.value.split(',').map(arg => arg.trim())
                  }
                }))}
                placeholder="e.g., -m, mcp_server"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Environment Variables (JSON)</label>
              <Textarea
                value={JSON.stringify(serverForm.connection_config.env || {}, null, 2)}
                onChange={(e) => {
                  try {
                    const env = JSON.parse(e.target.value);
                    setServerForm(prev => ({
                      ...prev,
                      connection_config: {
                        ...prev.connection_config,
                        env
                      }
                    }));
                  } catch {}
                }}
                rows={3}
                className="font-mono text-sm"
                placeholder='{"API_KEY": "your-key", "BASE_URL": "https://api.example.com"}'
              />
            </div>
          </div>
        );
      
      case 'http':
        return (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">Base URL</label>
              <Input
                value={serverForm.connection_config.base_url || ''}
                onChange={(e) => setServerForm(prev => ({
                  ...prev,
                  connection_config: {
                    ...prev.connection_config,
                    base_url: e.target.value
                  }
                }))}
                placeholder="e.g., https://api.example.com/mcp"
              />
            </div>
            {serverForm.requires_auth && (
              <div className="space-y-4 p-4 bg-zinc-50 dark:bg-zinc-800 rounded-lg">
                <div>
                  <label className="block text-sm font-medium mb-1">Authentication Type</label>
                  <Select
                    value={serverForm.auth_config?.type || 'bearer'}
                    onChange={(e) => setServerForm(prev => ({
                      ...prev,
                      auth_config: {
                        ...prev.auth_config,
                        type: e.target.value
                      }
                    }))}
                  >
                    <option value="bearer">Bearer Token</option>
                    <option value="api_key">API Key</option>
                  </Select>
                </div>
                {serverForm.auth_config?.type === 'bearer' && (
                  <div>
                    <label className="block text-sm font-medium mb-1">Bearer Token</label>
                    <Input
                      type="password"
                      value={serverForm.auth_config?.token || ''}
                      onChange={(e) => setServerForm(prev => ({
                        ...prev,
                        auth_config: {
                          ...prev.auth_config,
                          token: e.target.value
                        }
                      }))}
                    />
                  </div>
                )}
                {serverForm.auth_config?.type === 'api_key' && (
                  <>
                    <div>
                      <label className="block text-sm font-medium mb-1">Header Name</label>
                      <Input
                        value={serverForm.auth_config?.key_name || 'X-API-Key'}
                        onChange={(e) => setServerForm(prev => ({
                          ...prev,
                          auth_config: {
                            ...prev.auth_config,
                            key_name: e.target.value
                          }
                        }))}
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-1">API Key</label>
                      <Input
                        type="password"
                        value={serverForm.auth_config?.key_value || ''}
                        onChange={(e) => setServerForm(prev => ({
                          ...prev,
                          auth_config: {
                            ...prev.auth_config,
                            key_value: e.target.value
                          }
                        }))}
                      />
                    </div>
                  </>
                )}
              </div>
            )}
          </div>
        );
      
      case 'sse':
        return (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">SSE Endpoint URL</label>
              <Input
                value={serverForm.connection_config.url || ''}
                onChange={(e) => setServerForm(prev => ({
                  ...prev,
                  connection_config: {
                    ...prev.connection_config,
                    url: e.target.value
                  }
                }))}
                placeholder="e.g., https://api.example.com/mcp/sse"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Headers (JSON)</label>
              <Textarea
                value={JSON.stringify(serverForm.connection_config.headers || {}, null, 2)}
                onChange={(e) => {
                  try {
                    const headers = JSON.parse(e.target.value);
                    setServerForm(prev => ({
                      ...prev,
                      connection_config: {
                        ...prev.connection_config,
                        headers
                      }
                    }));
                  } catch {}
                }}
                rows={3}
                className="font-mono text-sm"
                placeholder='{"Authorization": "Bearer token", "Content-Type": "application/json"}'
              />
            </div>
          </div>
        );
      
      case 'websocket':
        return (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">WebSocket URL</label>
              <Input
                value={serverForm.connection_config.url || ''}
                onChange={(e) => setServerForm(prev => ({
                  ...prev,
                  connection_config: {
                    ...prev.connection_config,
                    url: e.target.value
                  }
                }))}
                placeholder="e.g., wss://api.example.com/mcp/ws"
              />
            </div>
          </div>
        );
      
      default:
        return null;
    }
  };

  const tabs = [
    { id: 'my-servers', label: 'My Servers', count: servers.length },
    { id: 'marketplace', label: 'Marketplace', count: marketplace.length }
  ];

  return (
    <div className="container mx-auto p-6 max-w-6xl">
      <div className="mb-6">
        <Button
          outline
          onClick={() => navigate('/admin')}
          className="mb-4"
        >
          <ChevronLeft className="h-4 w-4 mr-2" />
          Back to Admin
        </Button>
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2 mb-4">
              <Server className="h-8 w-8 text-orange-600" />
              <Heading level={1}>MCP Server Management</Heading>
            </div>
            <Text className="text-zinc-600 dark:text-zinc-400">
              Add and configure MCP servers for additional tool capabilities
            </Text>
          </div>
          <div className="flex gap-3">
            <Button outline onClick={() => setImportDialogOpen(true)}>
              <Upload className="h-4 w-4 mr-2" />
              Import from Claude
            </Button>
            <Button onClick={handleAddServer}>
              <Plus className="h-4 w-4 mr-2" />
              Add Server
            </Button>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-zinc-200 dark:border-zinc-800 mb-6">
        <div className="flex gap-6">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`pb-3 px-1 border-b-2 transition-colors flex items-center gap-2 ${
                activeTab === tab.id
                  ? 'border-indigo-600 text-indigo-600'
                  : 'border-transparent hover:border-zinc-300'
              }`}
            >
              <span className="font-medium">{tab.label}</span>
              <Badge color={activeTab === tab.id ? 'blue' : 'zinc'}>
                {tab.count}
              </Badge>
            </button>
          ))}
        </div>
      </div>

      {/* My Servers Tab */}
      {activeTab === 'my-servers' && (
        <div>
          {loading ? (
            <div className="flex justify-center py-12">
              <RefreshCw className="h-6 w-6 animate-spin text-zinc-400" />
            </div>
          ) : servers.length === 0 ? (
            <div className="text-center py-12 bg-zinc-50 dark:bg-zinc-900 rounded-lg">
              <Server className="h-12 w-12 text-zinc-400 mx-auto mb-4" />
              <Text className="text-zinc-600 dark:text-zinc-400">
                No MCP servers configured yet
              </Text>
              <Button onClick={handleAddServer} className="mt-4">
                <Plus className="h-4 w-4 mr-2" />
                Add Your First Server
              </Button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {servers.map(server => (
                <div
                  key={server.id}
                  className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg p-4"
                >
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-2">
                      {getServerIcon(server.server_type)}
                      <div>
                        <Text className="font-medium">{server.display_name}</Text>
                        <Text className="text-xs text-zinc-500">{server.name}</Text>
                      </div>
                    </div>
                    {getStatusBadge(server.status)}
                  </div>
                  
                  <Text className="text-sm text-zinc-600 dark:text-zinc-400 mb-3">
                    {server.description || 'No description'}
                  </Text>
                  
                  <div className="flex flex-wrap gap-2 mb-3">
                    <Badge color="zinc">
                      <Code className="h-3 w-3 mr-1" />
                      {server.tool_count} tools
                    </Badge>
                    <Badge color="zinc">
                      {server.usage_count} uses
                    </Badge>
                    {server.is_public && (
                      <Badge color="green">
                        <Unlock className="h-3 w-3 mr-1" />
                        Public
                      </Badge>
                    )}
                  </div>
                  
                  {server.last_connected && (
                    <Text className="text-xs text-zinc-500">
                      Last connected: {new Date(server.last_connected).toLocaleString()}
                    </Text>
                  )}
                  
                  <div className="flex gap-2 mt-4">
                    <Button size="sm" plain onClick={() => handleEditServer(server.id)}>
                      <Edit2 className="h-4 w-4" />
                    </Button>
                    <Button size="sm" plain onClick={() => setSelectedServer(server)}>
                      <PlayCircle className="h-4 w-4" />
                    </Button>
                    <Button size="sm" plain color="red" onClick={() => handleDeleteServer(server.id)}>
                      <Trash2 className="h-4 w-4" />
                    </Button>
                    {!server.is_public && (
                      <Button size="sm" plain>
                        <Share2 className="h-4 w-4" />
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Marketplace Tab */}
      {activeTab === 'marketplace' && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {marketplace.map(server => (
            <div
              key={server.id}
              className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg p-4"
            >
              <div className="flex items-center gap-2 mb-3">
                <Unlock className="h-5 w-5 text-green-600" />
                <Text className="font-medium">{server.display_name}</Text>
              </div>
              
              <Text className="text-sm text-zinc-600 dark:text-zinc-400 mb-3">
                {server.description}
              </Text>
              
              <div className="flex flex-wrap gap-2 mb-3">
                <Badge color="zinc">
                  {server.tool_count} tools
                </Badge>
                <Badge color="blue">
                  {server.usage_count} uses
                </Badge>
              </div>
              
              <Text className="text-xs text-zinc-500 mb-4">
                By {server.creator}
              </Text>
              
              <Button size="sm" outline className="w-full">
                <Plus className="h-4 w-4 mr-2" />
                Add to My Servers
              </Button>
            </div>
          ))}
        </div>
      )}

      {/* Add/Edit Server Dialog */}
      <Dialog open={dialogOpen} onClose={setDialogOpen}>
        <DialogTitle>
          {serverForm.id ? 'Edit MCP Server' : 'Add New MCP Server'}
        </DialogTitle>
        <DialogDescription>
          Configure the connection details for your MCP server
        </DialogDescription>
        
        <div className="mt-4 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Server Name (unique)</label>
              <Input
                value={serverForm.name}
                onChange={(e) => setServerForm(prev => ({ ...prev, name: e.target.value }))}
                placeholder="e.g., my_custom_tools"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Display Name</label>
              <Input
                value={serverForm.display_name}
                onChange={(e) => setServerForm(prev => ({ ...prev, display_name: e.target.value }))}
                placeholder="My Custom Tools"
              />
            </div>
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-1">Description</label>
            <Textarea
              value={serverForm.description}
              onChange={(e) => setServerForm(prev => ({ ...prev, description: e.target.value }))}
              rows={2}
              placeholder="What does this server provide?"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-1">Server Type</label>
            <Select
              value={serverForm.server_type}
              onChange={(e) => {
                const newType = e.target.value;
                // Initialize connection_config based on server type
                let newConfig = {};
                switch (newType) {
                  case 'stdio':
                    newConfig = {
                      command: '',
                      args: [],
                      env: {}
                    };
                    break;
                  case 'http':
                    newConfig = {
                      base_url: ''
                    };
                    break;
                  case 'sse':
                    newConfig = {
                      url: '',
                      headers: {}
                    };
                    break;
                  case 'websocket':
                    newConfig = {
                      url: ''
                    };
                    break;
                  default:
                    newConfig = {};
                }
                setServerForm(prev => ({ 
                  ...prev, 
                  server_type: newType,
                  connection_config: newConfig
                }));
              }}
            >
              <option value="stdio">STDIO (Local Command)</option>
              <option value="http">HTTP REST API</option>
              <option value="sse">Server-Sent Events</option>
              <option value="websocket">WebSocket</option>
            </Select>
          </div>
          
          {renderConnectionConfig()}
          
          {testResults && (
            <div className={`p-4 rounded-lg border ${
              testResults.success 
                ? 'bg-green-50 border-green-200 dark:bg-green-900/20 dark:border-green-800'
                : 'bg-red-50 border-red-200 dark:bg-red-900/20 dark:border-red-800'
            }`}>
              <div className="flex flex-col gap-2">
                <div className="flex items-center gap-2">
                  {testResults.success ? (
                    <>
                      <CheckCircle className="h-5 w-5 text-green-600" />
                      <Text className="text-green-800 dark:text-green-200">
                        Connected successfully! Found {testResults.tools?.length || 0} tools.
                      </Text>
                    </>
                  ) : (
                    <>
                      <XCircle className="h-5 w-5 text-red-600" />
                      <Text className="text-red-800 dark:text-red-200">
                        Connection failed: {testResults.error}
                      </Text>
                    </>
                  )}
                </div>
                {testResults.warning && (
                  <div className="flex items-center gap-2 ml-7">
                    <AlertCircle className="h-4 w-4 text-yellow-600" />
                    <Text className="text-sm text-yellow-700 dark:text-yellow-300">
                      {testResults.warning}
                    </Text>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
        
        <DialogActions>
          <Button plain onClick={() => setDialogOpen(false)}>
            Cancel
          </Button>
          <Button 
            outline
            onClick={handleTestServer} 
            disabled={testing}
          >
            {testing ? (
              <>
                <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                Testing...
              </>
            ) : (
              <>
                <PlayCircle className="h-4 w-4 mr-2" />
                Test Connection
              </>
            )}
          </Button>
          <Button 
            onClick={handleSaveServer} 
            disabled={!serverForm.name || !serverForm.display_name}
          >
            Save
          </Button>
        </DialogActions>
      </Dialog>

      {/* Test Results Dialog */}
      <Dialog open={testDialogOpen} onClose={setTestDialogOpen}>
        <DialogTitle>Test Results</DialogTitle>
        <DialogDescription>
          Server connection test completed successfully
        </DialogDescription>
        
        {testResults?.success && (
          <div className="mt-4">
            <div className="p-3 bg-green-50 dark:bg-green-900/20 rounded-lg mb-4">
              <div className="flex items-center gap-2">
                <CheckCircle className="h-5 w-5 text-green-600" />
                <Text className="font-medium">Server connected successfully!</Text>
              </div>
            </div>
            
            <Text className="font-medium mb-2">
              Available Tools ({testResults.tools?.length || 0}):
            </Text>
            
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {(testResults.tools || []).map((tool, index) => (
                <div key={index} className="flex items-start gap-2 p-2 bg-zinc-50 dark:bg-zinc-800 rounded">
                  <Code className="h-4 w-4 text-zinc-500 mt-0.5" />
                  <div>
                    <Text className="font-medium text-sm">
                      {tool.displayName || tool.name}
                    </Text>
                    <Text className="text-xs text-zinc-500">
                      {tool.description}
                    </Text>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
        
        <DialogActions>
          <Button plain onClick={() => setTestDialogOpen(false)}>
            Close
          </Button>
        </DialogActions>
      </Dialog>

      {/* Import Dialog */}
      <Dialog open={importDialogOpen} onClose={setImportDialogOpen}>
        <DialogTitle>Import from Claude Desktop</DialogTitle>
        <DialogDescription>
          Upload your Claude Desktop configuration file to import MCP servers
        </DialogDescription>
        
        <div className="mt-4">
          <Text className="text-sm mb-3">
            The configuration file is typically located at:
          </Text>
          <div className="p-3 bg-zinc-100 dark:bg-zinc-800 rounded font-mono text-xs mb-4">
            ~/Library/Application Support/Claude/claude_desktop_config.json
          </div>
          
          <input
            type="file"
            accept=".json"
            onChange={handleImportClaude}
            className="block w-full text-sm text-zinc-600 dark:text-zinc-400
              file:mr-4 file:py-2 file:px-4
              file:rounded-full file:border-0
              file:text-sm file:font-semibold
              file:bg-indigo-50 file:text-indigo-700
              hover:file:bg-indigo-100"
          />
        </div>
        
        <DialogActions>
          <Button plain onClick={() => setImportDialogOpen(false)}>
            Cancel
          </Button>
        </DialogActions>
      </Dialog>
    </div>
  );
};

export default MCPServerManager;