// Loader for AgentManagementPage - fetches directly from Python backend
const PYTHON_BACKEND_URL = 'http://localhost:8000';

export async function agentManagementLoader() {
  try {
    // Fetch all data in parallel
    const [agentsRes, modelsRes, statsRes] = await Promise.all([
      fetch(`${PYTHON_BACKEND_URL}/api/agent-management/agents`),
      fetch(`${PYTHON_BACKEND_URL}/api/agent-management/models`),
      fetch(`${PYTHON_BACKEND_URL}/api/agent-management/stats`)
    ]);

    const agentsData = await agentsRes.json();
    const modelsData = await modelsRes.json();
    const statsData = await statsRes.json();

    return {
      agents: agentsData.success ? agentsData.agents : [],
      models: modelsData.success ? modelsData.models : [],
      stats: statsData.success ? statsData.stats : null,
      provider: modelsData.provider || null,
      error: null
    };
  } catch (error) {
    console.error('Error loading agent management data:', error);
    return {
      agents: [],
      models: [],
      stats: null,
      provider: null,
      error: error.message
    };
  }
}