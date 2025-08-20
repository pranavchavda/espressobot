import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Heading } from '@common/heading';
import { Button } from '@common/button';
import { Text } from '@common/text';
import { Table, TableHead, TableBody, TableRow, TableHeader, TableCell } from '@common/table';
import { Dialog } from '@common/dialog';
import { Textarea } from '@common/textarea';
import { Select } from '@common/select';
import { Badge } from '@common/badge';
import { Settings, Edit, Eye, BarChart3, RotateCcw, Save, ChevronLeft, Bot, Trash2 } from 'lucide-react';

const AgentManagementPage = () => {
  const navigate = useNavigate();
  const [agents, setAgents] = useState([]);
  const [models, setModels] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [editingPrompt, setEditingPrompt] = useState(false);
  const [promptText, setPromptText] = useState('');
  const [activeTab, setActiveTab] = useState('agents');
  const [currentProvider, setCurrentProvider] = useState(null);
  
  // Python backend URL
  const PYTHON_BACKEND_URL = 'http://localhost:8000';

  // Load data on component mount
  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [agentsRes, modelsRes, statsRes] = await Promise.all([
        fetch(`${PYTHON_BACKEND_URL}/api/agent-management/agents`),
        fetch(`${PYTHON_BACKEND_URL}/api/agent-management/models`),
        fetch(`${PYTHON_BACKEND_URL}/api/agent-management/stats`)
      ]);

      const agentsData = await agentsRes.json();
      const modelsData = await modelsRes.json();
      const statsData = await statsRes.json();

      setAgents(agentsData.success ? agentsData.agents : []);
      
      if (modelsData.success) {
        setModels(modelsData.models);
        setCurrentProvider(modelsData.provider);
      }
      if (statsData.success) setStats(statsData.stats);

    } catch (error) {
      console.error('Error loading data:', error);
    } finally {
      setLoading(false);
    }
  };

  const syncAgents = async () => {
    try {
      const response = await fetch(`${PYTHON_BACKEND_URL}/api/agent-management/sync`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      });

      const result = await response.json();
      
      if (result.success) {
        console.log(`Synced ${result.synced} agents`);
        // Reload data to show newly synced agents
        await loadData();
      } else {
        console.error('Failed to sync agents:', result.error);
      }
    } catch (error) {
      console.error('Error syncing agents:', error);
    }
  };

  const updateAgentConfig = async (agentId, updates) => {
    // Validate inputs
    if (!agentId || !updates) {
      console.error('Invalid parameters:', { agentId, updates });
      alert('Error: Invalid agent ID or update data');
      return;
    }

    try {
      // Always route updates through agent-management; backend handles dynamic vs built-in
      console.log(`Updating agent ${agentId} with:`, updates);
      console.log('Request URL:', `${PYTHON_BACKEND_URL}/api/agent-management/agents/${agentId}`);
      const response = await fetch(`${PYTHON_BACKEND_URL}/api/agent-management/agents/${agentId}`, {
        method: 'PUT',
        headers: { 
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify(updates)
      });

      const result = await response.json();
      if (response.status === 422) {
        const details = result.detail?.map(d => d.msg).join(', ') || 'Validation error';
        alert('Failed to update agent: ' + details);
        return;
      }
      if (result.success) {
        loadData();
      } else {
        const errorMessage = result.error || result.detail || result.message || 'Unknown error';
        alert('Failed to update agent: ' + errorMessage);
      }
    } catch (error) {
      console.error('Error updating agent:', error);
      alert('Error updating agent: ' + error.message);
    }
  };

  const loadAgentPrompt = async (agent) => {
    try {
      let response;
      if (agent.source === 'dynamic') {
        // Load dynamic agent details
        response = await fetch(`${PYTHON_BACKEND_URL}/api/dynamic-agents/${agent.agent_name}`);
        const agentData = await response.json();
        setSelectedAgent(agent);
        setPromptText(agentData.system_prompt || '');
        setEditingPrompt(true);
      } else {
        // Load built-in agent prompt
        response = await fetch(`${PYTHON_BACKEND_URL}/api/agent-management/agents/${agent.id}/prompt`);
        const result = await response.json();
        
        if (result.success) {
          setSelectedAgent(agent);
          setPromptText(result.system_prompt || '');
          setEditingPrompt(true);
        }
      }
    } catch (error) {
      console.error('Error loading prompt:', error);
    }
  };

  const saveAgentPrompt = async () => {
    if (!selectedAgent) return;
    
    try {
      let response;
      if (selectedAgent && selectedAgent.source === 'dynamic') {
        // Update dynamic agent
        response = await fetch(`${PYTHON_BACKEND_URL}/api/dynamic-agents/${selectedAgent.agent_name}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ system_prompt: promptText })
        });
      } else {
        // Update built-in agent
        response = await fetch(`${PYTHON_BACKEND_URL}/api/agent-management/agents/${selectedAgent.id}/prompt`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ system_prompt: promptText })
        });
      }

      const result = await response.json();
      if (result.success || response.ok) {
        setEditingPrompt(false);
        setSelectedAgent(null);
        loadData(); // Refresh data
      } else {
        alert('Failed to save prompt: ' + (result.error || result.detail || 'Unknown error'));
      }
    } catch (error) {
      console.error('Error saving prompt:', error);
      alert('Error saving prompt');
    }
  };

  const deleteAgent = async (agent) => {
    if (!agent.is_dynamic) {
      alert('Cannot delete built-in agents');
      return;
    }

    if (!confirm(`Are you sure you want to delete the "${agent.agent_name}" agent? This action cannot be undone.`)) {
      return;
    }

    try {
      const response = await fetch(`${PYTHON_BACKEND_URL}/api/dynamic-agents/${agent.agent_name}`, {
        method: 'DELETE'
      });

      if (response.ok) {
        alert(`Agent "${agent.agent_name}" deleted successfully`);
        loadData(); // Refresh data
      } else {
        const result = await response.json();
        alert('Failed to delete agent: ' + (result.error || result.detail || 'Unknown error'));
      }
    } catch (error) {
      console.error('Error deleting agent:', error);
      alert('Error deleting agent: ' + error.message);
    }
  };

  const getProviderBadgeColor = (provider) => {
    if (!provider) return 'gray';
    const p = provider.toLowerCase();
    if (p.includes('openai') || p === 'openai') return 'green';
    if (p.includes('anthropic') || p === 'anthropic') return 'purple';
    if (p.includes('openrouter') || p === 'openrouter') return 'blue';
    if (p.includes('free')) return 'orange';
    return 'gray';
  };

  const getTypeIcon = (type) => {
    switch (type) {
      case 'orchestrator': return '🎯';
      case 'mcp': return '🔧';
      case 'specialized': return '⚡';
      default: return '🤖';
    }
  };

  if (loading) {
    return (
      <div className="container mx-auto p-6">
        <div className="flex items-center justify-center h-64">
          <Text className="text-lg">Loading agent configurations...</Text>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <Button
            outline
            onClick={() => navigate('/admin')}
            className="mb-4"
          >
            <ChevronLeft className="h-4 w-4 mr-2" />
            Back to Admin
          </Button>
          <Heading level={1}>Agent Management</Heading>
          <Text className="text-zinc-600 dark:text-zinc-400">
            Manage agent models and system prompts
          </Text>
        </div>
        <div className="flex gap-2">
          <Button onClick={syncAgents} outline>
            <Bot className="w-4 h-4 mr-2" />
            Sync Agents
          </Button>
          <Button onClick={loadData} outline>
            <RotateCcw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="border-b border-zinc-200 dark:border-zinc-700 mb-6">
        <nav className="-mb-px flex space-x-8">
          {[
            { id: 'agents', label: `Agents (${agents.length})`, icon: Bot },
            { id: 'models', label: `Models (${models.length})`, icon: Settings },
            { id: 'stats', label: 'Statistics', icon: BarChart3 }
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === tab.id
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-zinc-500 hover:text-zinc-700 hover:border-zinc-300'
              }`}
            >
              <tab.icon className="w-4 h-4 mr-2" />
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Agents Tab */}
      {activeTab === 'agents' && (
        <div className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {agents.map((agent) => (
              <div key={agent.id} className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg p-6 hover:shadow-md transition-shadow">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-lg">{getTypeIcon(agent.agent_type)}</span>
                      <Heading level={3} className="text-lg">{agent.agent_name}</Heading>
                    </div>
                    <div className="flex gap-2 mb-2">
                      <Badge color={agent.agent_type === 'orchestrator' ? 'blue' : 'gray'}>
                        {agent.agent_type}
                      </Badge>
                      <Badge color={agent.source === 'dynamic' ? 'purple' : agent.source === 'database' ? 'green' : agent.source === 'file' ? 'orange' : 'gray'}>
                        {agent.source || 'database'}
                      </Badge>
                      {agent.is_dynamic && (
                        <Badge color="indigo">
                          User-created
                        </Badge>
                      )}
                      {!agent.configurable && !agent.is_dynamic && (
                        <Badge color="red">
                          Read-only
                        </Badge>
                      )}
                    </div>
                  </div>
                  {agent.is_dynamic ? (
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        outline
                        onClick={() => navigate(`/admin/agents/edit/${agent.dynamic_name}`)}
                        title="Edit in Agent Builder"
                      >
                        <Edit className="w-4 h-4" />
                      </Button>
                      <Button
                        size="sm"
                        outline
                        onClick={() => deleteAgent(agent)}
                        title="Delete Agent"
                        className="text-red-600 hover:text-red-700 hover:bg-red-50"
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  ) : (
                    <Button
                      size="sm"
                      outline
                      onClick={() => loadAgentPrompt(agent)}
                      title="Edit system prompt"
                      disabled={!agent.configurable}
                    >
                      <Edit className="w-4 h-4" />
                    </Button>
                  )}
                </div>
                
                <div className="space-y-3">
                  <div>
                    <Text className="text-sm text-zinc-600 dark:text-zinc-400 font-medium">Current Configuration</Text>
                    <div className="mt-1 space-y-1">
                      <Badge color={getProviderBadgeColor(agent.model_provider || 'openrouter')} className="mr-2">
                        {agent.model_provider || 'openrouter'}
                      </Badge>
                      <Badge color="gray">
                        {agent.model_slug || agent.model_name}
                      </Badge>
                    </div>
                    {agent.hardcoded_model && agent.hardcoded_model !== agent.model_slug && (
                      <div className="mt-1">
                        <Text className="text-xs text-zinc-500">Hardcoded: {agent.hardcoded_model}</Text>
                      </div>
                    )}
                  </div>
                  
                  <div>
                    <Text className="text-sm text-zinc-600 dark:text-zinc-400 font-medium mb-2">Provider</Text>
                    <Select
                      value={agent.model_provider || 'openrouter'}
                      onChange={(e) => updateAgentConfig(agent.id, { model_provider: e.target.value })}
                      className="w-full mb-2"
                    >
                      <option value="openai">OpenAI (Direct)</option>
                      <option value="anthropic">Anthropic (Direct)</option>
                      <option value="openrouter">OpenRouter (Proxy)</option>
                    </Select>
                    
                    <Text className="text-sm text-zinc-600 dark:text-zinc-400 font-medium mb-2">Model</Text>
                    <Select
                      value={agent.model_slug}
                      onChange={(e) => updateAgentConfig(agent.id, { model_slug: e.target.value })}
                      className="w-full"
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
                  </div>

                  {agent.description && (
                    <Text className="text-sm text-zinc-600 dark:text-zinc-400">
                      {agent.description}
                    </Text>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Models Tab */}
      {activeTab === 'models' && (
        <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg">
          <div className="p-6 border-b border-zinc-200 dark:border-zinc-800">
            <div className="flex items-center justify-between">
              <Heading level={2}>Available Models ({models.length})</Heading>
              {currentProvider && (
                <Badge color={currentProvider === 'openai' ? 'green' : currentProvider === 'anthropic' ? 'purple' : 'blue'} size="lg">
                  Provider: {currentProvider.toUpperCase()}
                </Badge>
              )}
            </div>
          </div>
          <div className="p-6">
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {models.slice(0, 50).map((model) => (
                <div key={model.id} className="flex items-center justify-between p-3 border border-zinc-200 dark:border-zinc-800 rounded">
                  <div>
                    <Text className="font-medium">{model.name}</Text>
                    <Text className="text-sm text-zinc-600 dark:text-zinc-400">{model.id}</Text>
                  </div>
                  <div className="flex gap-2">
                    <Badge color="gray" outline>{model.provider}</Badge>
                    {model.id.includes('free') && (
                      <Badge color="green">Free</Badge>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Stats Tab */}
      {activeTab === 'stats' && stats && (
        <div className="grid gap-4 md:grid-cols-2">
          <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg p-6">
            <Heading level={2} className="mb-4">Overview</Heading>
            <div className="space-y-2">
              <div className="flex justify-between">
                <Text>Total Agents:</Text>
                <Badge>{stats.totals.total_agents}</Badge>
              </div>
              <div className="flex justify-between">
                <Text>Active Agents:</Text>
                <Badge outline>{stats.totals.active_agents}</Badge>
              </div>
              <div className="flex justify-between">
                <Text>Unique Models:</Text>
                <Badge outline>{stats.totals.unique_models}</Badge>
              </div>
              <div className="flex justify-between">
                <Text>With Custom Prompts:</Text>
                <Badge outline>{stats.totals.agents_with_prompts}</Badge>
              </div>
            </div>
          </div>

          <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg p-6">
            <Heading level={2} className="mb-4">By Type</Heading>
            <div className="space-y-2">
              {stats.by_type.map((stat) => (
                <div key={stat.agent_type} className="flex justify-between">
                  <Text className="capitalize">{stat.agent_type}:</Text>
                  <Badge>{stat.count} ({stat.active_count} active)</Badge>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Prompt Editor Dialog */}
      {editingPrompt && (
        <Dialog open={editingPrompt} onClose={() => setEditingPrompt(false)}>
          <div className="max-w-4xl max-h-[80vh] overflow-y-auto p-6">
            <Heading level={2} className="mb-4">
              Edit System Prompt - {selectedAgent?.agent_name}
            </Heading>
            <div className="space-y-4">
              <Textarea
                value={promptText}
                onChange={(e) => setPromptText(e.target.value)}
                placeholder="Enter system prompt..."
                className="min-h-[400px] font-mono text-sm"
                rows={20}
              />
              <div className="flex justify-end gap-2">
                <Button outline onClick={() => setEditingPrompt(false)}>
                  Cancel
                </Button>
                <Button onClick={saveAgentPrompt}>
                  <Save className="w-4 h-4 mr-2" />
                  Save Prompt
                </Button>
              </div>
            </div>
          </div>
        </Dialog>
      )}
    </div>
  );
};

export default AgentManagementPage;
