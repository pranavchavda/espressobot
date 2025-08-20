import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
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
  Save, 
  PlayCircle, 
  Copy, 
  Code, 
  Brain, 
  Wrench, 
  Route,
  ChevronLeft,
  AlertCircle,
  CheckCircle
} from 'lucide-react';

const AgentBuilder = () => {
  const navigate = useNavigate();
  const { agentName } = useParams();
  const [isEditMode, setIsEditMode] = useState(false);
  const [activeTab, setActiveTab] = useState('prompt');
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testQuery, setTestQuery] = useState('');
  const [testResult, setTestResult] = useState(null);
  const [templateDialog, setTemplateDialog] = useState(false);
  const [templates, setTemplates] = useState([]);
  const [availableMCPServers, setAvailableMCPServers] = useState([]);
  
  const [agent, setAgent] = useState({
    name: '',
    display_name: '',
    description: '',
    agent_type: 'specialist',
    system_prompt: '',
    model_provider: 'openai',
    model_name: 'gpt-4o-mini',
    temperature: null,
    max_tokens: null,
    max_completion_tokens: null,
    tools: [],
    mcp_servers: [],
    capabilities: [],
    routing_keywords: [],
    example_queries: []
  });

  // State for custom model input (OpenRouter)
  const [useCustomModel, setUseCustomModel] = useState(false);

  // Dynamic model options from API
  const [models, setModels] = useState([]);
  const modelProviders = ['openai', 'anthropic', 'openrouter'];

  useEffect(() => {
    loadAvailableResources();
    loadTemplates();
    loadModels();
    
    // If we have an agent name in the URL, load the agent for editing
    if (agentName) {
      setIsEditMode(true);
      loadAgent(agentName);
    }
  }, [agentName]);
  
  const loadAgent = async (name) => {
    try {
      const response = await fetch(`http://localhost:8000/api/dynamic-agents/${name}`);
      if (response.ok) {
        const data = await response.json();
        console.log('Loaded agent data:', data);
        
        // Handle temperature - it might be null, a number, or an object with value
        let temperatureValue = null;
        if (data.temperature !== null && data.temperature !== undefined) {
          if (typeof data.temperature === 'object' && data.temperature.value !== undefined) {
            temperatureValue = data.temperature.value;
          } else if (typeof data.temperature === 'number') {
            temperatureValue = data.temperature;
          }
        }
        
        setAgent({
          name: data.name || '',
          display_name: data.display_name || '',
          description: data.description || '',
          agent_type: data.agent_type || 'specialist',
          system_prompt: data.system_prompt || '',
          model_provider: data.model_provider || 'openai',
          model_name: data.model_name || 'gpt-4o-mini',
          temperature: temperatureValue,
          max_tokens: data.max_tokens || null,
          max_completion_tokens: data.max_completion_tokens || null,
          tools: data.tools || [],
          mcp_servers: data.mcp_servers || [],
          capabilities: data.capabilities || [],
          routing_keywords: data.routing_keywords || [],
          example_queries: data.example_queries || []
        });
        
        // Check if we should show custom model input
        const isCustomModel = data.model_provider === 'openrouter' && 
          !models.some(model => model.id === data.model_name);
        setUseCustomModel(isCustomModel);
      } else {
        const errorText = await response.text();
        console.error('Failed to load agent:', response.status, errorText);
        alert(`Failed to load agent: ${response.status} ${response.statusText}`);
        navigate('/admin/agents');
      }
    } catch (error) {
      console.error('Error loading agent:', error);
      alert(`Error loading agent: ${error.message}`);
      navigate('/admin/agents');
    }
  };

  const loadAvailableResources = async () => {
    try {
      const serversResponse = await fetch('http://localhost:8000/api/user-mcp-servers');
      const servers = await serversResponse.json();
      setAvailableMCPServers(servers);
    } catch (error) {
      console.error('Failed to load resources:', error);
    }
  };

  const loadModels = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/agent-management/models');
      const data = await response.json();
      if (data.success) {
        setModels(data.models);
      }
    } catch (error) {
      console.error('Failed to load models:', error);
    }
  };

  const loadTemplates = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/dynamic-agents/templates/');
      const data = await response.json();
      setTemplates(data);
    } catch (error) {
      console.error('Failed to load templates:', error);
    }
  };

  const handleInputChange = (field, value) => {
    setAgent(prev => ({ ...prev, [field]: value }));
  };

  const handleArrayAdd = (field, value) => {
    if (value && !agent[field].includes(value)) {
      setAgent(prev => ({
        ...prev,
        [field]: [...prev[field], value]
      }));
    }
  };

  const handleArrayRemove = (field, index) => {
    setAgent(prev => ({
      ...prev,
      [field]: prev[field].filter((_, i) => i !== index)
    }));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const url = isEditMode 
        ? `/api/dynamic-agents/${agent.name}`
        : '/api/dynamic-agents/';
      
      const method = isEditMode ? 'PUT' : 'POST';
      
      const response = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(agent)
      });
      
      const text = await response.text();
      
      if (response.ok) {
        try {
          const result = text ? JSON.parse(text) : {};
          console.log(`Agent ${isEditMode ? 'updated' : 'created'} successfully:`, result);
          alert(`Agent "${result.name || agent.name}" ${isEditMode ? 'updated' : 'created'} successfully!`);
          navigate('/agent-management');
        } catch (parseError) {
          console.error('Failed to parse success response:', text);
          alert(`Agent ${isEditMode ? 'updated' : 'created'} successfully!`);
          navigate('/agent-management');
        }
      } else {
        // Handle error response
        let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
        try {
          const error = text ? JSON.parse(text) : {};
          errorMessage = error.detail || error.message || text || errorMessage;
        } catch (parseError) {
          errorMessage = text || errorMessage;
        }
        alert(`Error: ${errorMessage}`);
      }
    } catch (error) {
      alert(`Failed to save agent: ${error.message}`);
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async () => {
    if (!testQuery) {
      alert('Please enter a test query');
      return;
    }

    setTesting(true);
    try {
      const response = await fetch(`http://localhost:8000/api/dynamic-agents/${agent.name}/test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: testQuery })
      });
      
      const result = await response.json();
      setTestResult(result);
    } catch (error) {
      setTestResult({ error: error.message });
    } finally {
      setTesting(false);
    }
  };

  const loadTemplate = async (templateName) => {
    try {
      const response = await fetch('http://localhost:8000/api/dynamic-agents/templates/' + templateName);
      const template = await response.json();
      setAgent(prev => ({
        ...prev,
        ...template.config,
        name: prev.name // Keep the custom name
      }));
      setTemplateDialog(false);
    } catch (error) {
      alert('Failed to load template: ' + error.message);
    }
  };

  const tabs = [
    { id: 'prompt', label: 'System Prompt', icon: <Code className="h-4 w-4" /> },
    { id: 'model', label: 'Model Config', icon: <Brain className="h-4 w-4" /> },
    { id: 'tools', label: 'Tools & MCP', icon: <Wrench className="h-4 w-4" /> },
    { id: 'routing', label: 'Routing', icon: <Route className="h-4 w-4" /> },
    { id: 'test', label: 'Test', icon: <PlayCircle className="h-4 w-4" /> }
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
        <div className="flex items-center gap-2 mb-4">
          <Brain className="h-8 w-8 text-indigo-600" />
          <Heading level={1}>{isEditMode ? 'Edit Agent' : 'Agent Builder'}</Heading>
        </div>
        <Text className="text-zinc-600 dark:text-zinc-400">
          {isEditMode ? 'Modify your custom agent configuration' : 'Create and configure custom agents without writing code'}
        </Text>
      </div>

      {/* Basic Info */}
      <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg p-6 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">Agent Name (unique)</label>
            <Input
              value={agent.name}
              onChange={(e) => handleInputChange('name', e.target.value)}
              placeholder="e.g., customer_support"
              disabled={isEditMode}
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Display Name</label>
            <Input
              value={agent.display_name}
              onChange={(e) => handleInputChange('display_name', e.target.value)}
              placeholder="Customer Support Agent"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Agent Type</label>
            <Select
              value={agent.agent_type}
              onChange={(e) => handleInputChange('agent_type', e.target.value)}
            >
              <option value="specialist">Specialist</option>
              <option value="orchestrator">Orchestrator</option>
              <option value="analyzer">Analyzer</option>
            </Select>
          </div>
        </div>
        <div className="mt-4">
          <label className="block text-sm font-medium mb-1">Description</label>
          <Textarea
            value={agent.description}
            onChange={(e) => handleInputChange('description', e.target.value)}
            rows={2}
            placeholder="Brief description of what this agent does..."
          />
        </div>
        <div className="mt-4">
          <Button outline onClick={() => setTemplateDialog(true)}>
            <Copy className="h-4 w-4 mr-2" />
            Use Template
          </Button>
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg">
        <div className="border-b border-zinc-200 dark:border-zinc-800">
          <div className="flex gap-4 p-4">
            {tabs.map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-colors ${
                  activeTab === tab.id
                    ? 'bg-zinc-100 dark:bg-zinc-800 text-zinc-900 dark:text-white'
                    : 'hover:bg-zinc-50 dark:hover:bg-zinc-800/50'
                }`}
              >
                {tab.icon}
                <span className="text-sm font-medium">{tab.label}</span>
              </button>
            ))}
          </div>
        </div>

        <div className="p-6">
          {/* System Prompt Tab */}
          {activeTab === 'prompt' && (
            <div>
              <Heading level={3} className="mb-4">System Prompt</Heading>
              <Textarea
                value={agent.system_prompt}
                onChange={(e) => handleInputChange('system_prompt', e.target.value)}
                rows={15}
                placeholder="Define your agent's personality, capabilities, and behavior..."
                className="font-mono text-sm"
              />
              <Text className="text-sm text-zinc-500 mt-2">
                Define your agent's personality, capabilities, and behavior
              </Text>
            </div>
          )}

          {/* Model Configuration Tab */}
          {activeTab === 'model' && (
            <div>
              <Heading level={3} className="mb-4">Model Configuration</Heading>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Model Provider</label>
                  <Select
                    value={agent.model_provider}
                    onChange={(e) => {
                      handleInputChange('model_provider', e.target.value);
                      // Reset custom model state when provider changes
                      if (e.target.value !== 'openrouter') {
                        setUseCustomModel(false);
                      }
                    }}
                  >
                    {modelProviders.map(provider => (
                      <option key={provider} value={provider}>{provider}</option>
                    ))}
                  </Select>
                </div>
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <label className="block text-sm font-medium">Model Name</label>
                    {agent.model_provider === 'openrouter' && (
                      <button
                        type="button"
                        onClick={() => setUseCustomModel(!useCustomModel)}
                        className="text-xs text-blue-600 hover:text-blue-700 dark:text-blue-400"
                      >
                        {useCustomModel ? 'Use Dropdown' : 'Enter Custom Model'}
                      </button>
                    )}
                  </div>
                  {agent.model_provider === 'openrouter' && useCustomModel ? (
                    <Input
                      value={agent.model_name}
                      onChange={(e) => handleInputChange('model_name', e.target.value)}
                      placeholder="e.g., meta-llama/llama-3.2-3b-instruct:free"
                    />
                  ) : (
                    <Select
                      value={agent.model_name}
                      onChange={(e) => handleInputChange('model_name', e.target.value)}
                    >
                      {models
                        .filter(model => {
                          // Filter models based on selected provider
                          const provider = agent.model_provider || 'openrouter';
                          if (provider === 'openai') {
                            return model.id.startsWith('gpt') || model.id.startsWith('o1');
                          } else if (provider === 'anthropic') {
                            return model.id.includes('claude');
                          } else {
                            // OpenRouter - show all
                            return true;
                          }
                        })
                        .map((model) => (
                          <option key={model.id} value={model.id}>
                            {model.name} {model.id.includes('free') ? ' - Free' : ''}
                          </option>
                        ))}
                    </Select>
                  )}
                  {agent.model_provider === 'openrouter' && useCustomModel && (
                    <Text className="text-xs text-zinc-500 mt-1">
                      Enter any OpenRouter model slug (e.g., meta-llama/llama-3.2-3b-instruct:free)
                    </Text>
                  )}
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">
                    Temperature <span className="text-xs text-zinc-500">(optional)</span>
                  </label>
                  <Input
                    type="number"
                    value={agent.temperature || ''}
                    onChange={(e) => handleInputChange('temperature', e.target.value ? parseFloat(e.target.value) : null)}
                    min="0"
                    max="2"
                    step="0.1"
                    placeholder="Default"
                  />
                </div>
                {agent.model_provider === 'openai' ? (
                  <div>
                    <label className="block text-sm font-medium mb-1">
                      Max Completion Tokens <span className="text-xs text-zinc-500">(optional)</span>
                    </label>
                    <Input
                      type="number"
                      value={agent.max_completion_tokens || ''}
                      onChange={(e) => handleInputChange('max_completion_tokens', e.target.value ? parseInt(e.target.value) : null)}
                      min="100"
                      max="16384"
                      placeholder="Default"
                    />
                  </div>
                ) : (
                  <div>
                    <label className="block text-sm font-medium mb-1">
                      Max Tokens <span className="text-xs text-zinc-500">(optional)</span>
                    </label>
                    <Input
                      type="number"
                      value={agent.max_tokens || ''}
                      onChange={(e) => handleInputChange('max_tokens', e.target.value ? parseInt(e.target.value) : null)}
                      min="100"
                      max="8192"
                      placeholder="Default"
                    />
                  </div>
                )}
              </div>
              <Text className="text-sm text-zinc-500 mt-4">
                Note: Some models may not support temperature or token limits. Leave optional fields empty to use model defaults.
              </Text>
            </div>
          )}

          {/* Tools & MCP Tab */}
          {activeTab === 'tools' && (
            <div>
              <Heading level={3} className="mb-4">Tools & MCP Servers</Heading>
              
              <div className="mb-6">
                <label className="block text-sm font-medium mb-2">MCP Servers ({agent.mcp_servers.length})</label>
                <div className="flex flex-wrap gap-2 mb-2">
                  {agent.mcp_servers.map((server, index) => (
                    <Badge key={index} color="blue">
                      {server}
                      <button
                        onClick={() => handleArrayRemove('mcp_servers', index)}
                        className="ml-2"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </Badge>
                  ))}
                </div>
                <Select onChange={(e) => {
                  if (e.target.value) {
                    handleArrayAdd('mcp_servers', e.target.value);
                    e.target.value = '';
                  }
                }}>
                  <option value="">Select MCP Server...</option>
                  {availableMCPServers.map(server => (
                    <option key={server.id} value={server.name}>
                      {server.display_name || server.name}
                    </option>
                  ))}
                </Select>
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">Custom Tools</label>
                <Text className="text-sm text-zinc-500">
                  Configure custom tools for this agent (coming soon)
                </Text>
              </div>
            </div>
          )}

          {/* Routing Tab */}
          {activeTab === 'routing' && (
            <div>
              <Heading level={3} className="mb-4">Routing Configuration</Heading>
              
              <div className="mb-6">
                <label className="block text-sm font-medium mb-2">Capabilities</label>
                <div className="flex flex-wrap gap-2 mb-2">
                  {agent.capabilities.map((cap, index) => (
                    <Badge key={index} color="green">
                      {cap}
                      <button
                        onClick={() => handleArrayRemove('capabilities', index)}
                        className="ml-2"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </Badge>
                  ))}
                </div>
                <Input
                  placeholder="Add capability and press Enter..."
                  onKeyPress={(e) => {
                    if (e.key === 'Enter') {
                      handleArrayAdd('capabilities', e.target.value);
                      e.target.value = '';
                    }
                  }}
                />
              </div>

              <div className="mb-6">
                <label className="block text-sm font-medium mb-2">Routing Keywords</label>
                <div className="flex flex-wrap gap-2 mb-2">
                  {agent.routing_keywords.map((keyword, index) => (
                    <Badge key={index} color="purple">
                      {keyword}
                      <button
                        onClick={() => handleArrayRemove('routing_keywords', index)}
                        className="ml-2"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </Badge>
                  ))}
                </div>
                <Input
                  placeholder="Add keyword and press Enter..."
                  onKeyPress={(e) => {
                    if (e.key === 'Enter') {
                      handleArrayAdd('routing_keywords', e.target.value);
                      e.target.value = '';
                    }
                  }}
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">Example Queries</label>
                <div className="space-y-2 mb-2">
                  {agent.example_queries.map((query, index) => (
                    <div key={index} className="flex items-center gap-2">
                      <Text className="flex-1">{query}</Text>
                      <button
                        onClick={() => handleArrayRemove('example_queries', index)}
                        className="text-red-500"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    </div>
                  ))}
                </div>
                <Input
                  placeholder="Add example query and press Enter..."
                  onKeyPress={(e) => {
                    if (e.key === 'Enter') {
                      handleArrayAdd('example_queries', e.target.value);
                      e.target.value = '';
                    }
                  }}
                />
              </div>
            </div>
          )}

          {/* Test Tab */}
          {activeTab === 'test' && (
            <div>
              <Heading level={3} className="mb-4">Test Agent</Heading>
              
              <div className="mb-4">
                <label className="block text-sm font-medium mb-2">Test Query</label>
                <Textarea
                  value={testQuery}
                  onChange={(e) => setTestQuery(e.target.value)}
                  rows={3}
                  placeholder="Enter a query to test if this agent can handle it..."
                />
              </div>
              
              <Button
                onClick={handleTest}
                disabled={testing || !agent.name}
              >
                <PlayCircle className="h-4 w-4 mr-2" />
                {testing ? 'Testing...' : 'Test Agent'}
              </Button>

              {testResult && (
                <div className={`mt-4 p-4 rounded-lg border ${
                  testResult.can_handle 
                    ? 'bg-green-50 border-green-200 dark:bg-green-900/20 dark:border-green-800'
                    : 'bg-yellow-50 border-yellow-200 dark:bg-yellow-900/20 dark:border-yellow-800'
                }`}>
                  <div className="flex items-center gap-2 mb-2">
                    {testResult.can_handle ? (
                      <>
                        <CheckCircle className="h-5 w-5 text-green-600" />
                        <Text className="font-medium">Agent CAN handle this query</Text>
                      </>
                    ) : (
                      <>
                        <AlertCircle className="h-5 w-5 text-yellow-600" />
                        <Text className="font-medium">Agent CANNOT handle this query</Text>
                      </>
                    )}
                  </div>
                  {testResult.matched_keywords && testResult.matched_keywords.length > 0 && (
                    <Text className="text-sm">
                      Matched keywords: {testResult.matched_keywords.join(', ')}
                    </Text>
                  )}
                  {testResult.error && (
                    <Text className="text-sm text-red-600">
                      Error: {testResult.error}
                    </Text>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Action Buttons */}
      <div className="mt-6 flex gap-3 justify-end">
        <Button
          outline
          onClick={() => {
            setAgent({
              name: '',
              display_name: '',
              description: '',
              agent_type: 'specialist',
              system_prompt: '',
              model_provider: 'openai',
              model_name: 'gpt-4o-mini',
              temperature: null,
              max_tokens: null,
              max_completion_tokens: null,
              tools: [],
              mcp_servers: [],
              capabilities: [],
              routing_keywords: [],
              example_queries: []
            });
            setUseCustomModel(false);
          }}
        >
          Clear
        </Button>
        <Button
          onClick={handleSave}
          disabled={saving || !agent.name || !agent.display_name || !agent.system_prompt}
        >
          <Save className="h-4 w-4 mr-2" />
          {saving ? 'Saving...' : isEditMode ? 'Update Agent' : 'Save Agent'}
        </Button>
      </div>

      {/* Template Dialog */}
      <Dialog open={templateDialog} onClose={setTemplateDialog}>
        <DialogTitle>Choose a Template</DialogTitle>
        <DialogDescription>
          Select a pre-built template to get started quickly
        </DialogDescription>
        <div className="mt-4 space-y-2">
          {templates.map(template => (
            <button
              key={template.name}
              onClick={() => loadTemplate(template.name)}
              className="w-full text-left p-3 rounded-lg border border-zinc-200 dark:border-zinc-700 hover:bg-zinc-50 dark:hover:bg-zinc-800"
            >
              <div className="font-medium">{template.name}</div>
              <div className="text-sm text-zinc-600 dark:text-zinc-400">
                {template.description}
              </div>
              <div className="text-xs text-zinc-500 mt-1">
                Category: {template.category} | Used {template.usage_count} times
              </div>
            </button>
          ))}
        </div>
        <DialogActions>
          <Button plain onClick={() => setTemplateDialog(false)}>
            Cancel
          </Button>
        </DialogActions>
      </Dialog>
    </div>
  );
};

export default AgentBuilder;