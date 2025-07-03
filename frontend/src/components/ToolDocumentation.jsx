import React, { useState, useEffect } from 'react';
import { Search, Terminal, BookOpen, Tag } from 'lucide-react';

const ToolDocumentation = () => {
  const [tools, setTools] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [selectedTool, setSelectedTool] = useState(null);
  const [showFullDocs, setShowFullDocs] = useState(false);

  // Tool type colors
  const toolTypeColors = {
    python: 'bg-green-100 text-green-800',
    orchestrator: 'bg-blue-100 text-blue-800',
    bash: 'bg-yellow-100 text-yellow-800',
    guide: 'bg-purple-100 text-purple-800'
  };

  const priorityColors = {
    high: 'bg-red-100 text-red-800',
    medium: 'bg-yellow-100 text-yellow-800',
    low: 'bg-green-100 text-green-800'
  };

  useEffect(() => {
    fetchTools();
  }, []);

  const fetchTools = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('authToken');
      const response = await fetch('/api/prompt-library?category=tools', {
        credentials: 'include',
        headers: {
          'Authorization': token ? `Bearer ${token}` : ''
        }
      });
      
      if (!response.ok) {
        throw new Error('Failed to fetch tool documentation');
      }
      
      const data = await response.json();
      console.log('API Response:', data);
      
      // Filter and process tools
      const toolData = (data.fragments || [])
        .filter(fragment => fragment.metadata?.tool_name && fragment.metadata.tool_name.trim())
        .map(fragment => ({
          name: fragment.metadata.tool_name || 'Unknown Tool',
          type: fragment.metadata.tool_type || 'unknown',
          priority: fragment.metadata.priority || 'medium',
          tags: fragment.metadata.tags || [],
          content: fragment.memory || '',
          id: fragment.id,
          metadata: fragment.metadata
        }))
        .filter(tool => tool.name && tool.name !== 'Unknown Tool') // Extra safety check
        .sort((a, b) => a.name.localeCompare(b.name));
      
      console.log('Processed tool data:', toolData.length, 'tools');
      console.log('Sample tools:', toolData.slice(0, 3).map(t => ({ name: t.name, type: t.type })));
      
      setTools(toolData);
    } catch (err) {
      console.error('Error fetching tools:', err);
      setError(`Error loading tool documentation: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const filteredTools = tools.filter(tool => {
    // Safety checks to prevent undefined errors
    if (!tool || !tool.name) return false;
    
    const toolName = (tool.name || '').toLowerCase();
    const toolContent = (tool.content || '').toLowerCase();
    const toolTags = tool.tags || [];
    const query = searchQuery.toLowerCase();
    
    const matchesSearch = toolName.includes(query) ||
                         toolTags.some(tag => (tag || '').toLowerCase().includes(query)) ||
                         toolContent.includes(query);
    
    const matchesCategory = selectedCategory === 'all' || tool.type === selectedCategory;
    
    return matchesSearch && matchesCategory;
  });

  const groupedTools = filteredTools.reduce((groups, tool) => {
    const type = tool.type;
    if (!groups[type]) {
      groups[type] = [];
    }
    groups[type].push(tool);
    return groups;
  }, {});

  const extractPurpose = (content) => {
    const purposeMatch = content.match(/\*\*Purpose\*\*:\s*(.+?)(?:\n|\*\*)/);
    return purposeMatch ? purposeMatch[1] : 'No description available';
  };

  const extractPath = (content) => {
    const pathMatch = content.match(/\*\*Python Path\*\*:\s*(.+?)(?:\n|\*\*)/);
    const accessMatch = content.match(/\*\*Access\*\*:\s*(.+?)(?:\n|\*\*)/);
    return pathMatch ? pathMatch[1] : accessMatch ? accessMatch[1] : '';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <div className="flex">
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">
                Error loading tool documentation
              </h3>
              <div className="mt-2 text-sm text-red-700">
                <p>{error}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-white shadow-sm rounded-lg">
          {/* Header */}
          <div className="px-6 py-4 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-2xl font-bold text-gray-900 flex items-center">
                  <BookOpen className="h-8 w-8 mr-2 text-indigo-600" />
                  Tool Documentation
                </h1>
                <p className="mt-1 text-sm text-gray-600">
                  Comprehensive documentation for all available tools and utilities
                </p>
              </div>
              <div className="flex items-center space-x-2">
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-800">
                  {tools.length} tools available
                </span>
              </div>
            </div>
          </div>

          {/* Search and Filters */}
          <div className="px-6 py-4 border-b border-gray-200 bg-gray-50">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between space-y-3 sm:space-y-0 sm:space-x-4">
              <div className="flex-1 max-w-lg">
                <label htmlFor="search" className="sr-only">Search tools</label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <Search className="h-5 w-5 text-gray-400" />
                  </div>
                  <input
                    id="search"
                    name="search"
                    className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md leading-5 bg-white placeholder-gray-500 focus:outline-none focus:placeholder-gray-400 focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                    placeholder="Search tools by name, tags, or description..."
                    type="search"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                  />
                </div>
              </div>
              
              <div className="flex items-center space-x-4">
                <select
                  value={selectedCategory}
                  onChange={(e) => setSelectedCategory(e.target.value)}
                  className="block pl-3 pr-10 py-2 text-base border border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md"
                >
                  <option value="all">All Types</option>
                  <option value="python">Python Tools</option>
                  <option value="orchestrator">Orchestrator Tools</option>
                  <option value="bash">Bash Tools</option>
                  <option value="guide">Guides</option>
                </select>
              </div>
            </div>
          </div>

          {/* Tools List */}
          <div className="divide-y divide-gray-200">
            {Object.keys(groupedTools).length === 0 ? (
              <div className="px-6 py-12 text-center">
                <Terminal className="mx-auto h-12 w-12 text-gray-400" />
                <h3 className="mt-2 text-sm font-medium text-gray-900">No tools found</h3>
                <p className="mt-1 text-sm text-gray-500">
                  Try adjusting your search query or filters.
                </p>
              </div>
            ) : (
              Object.entries(groupedTools).map(([type, typeTools]) => (
                <div key={type} className="px-6 py-4">
                  <h2 className="text-lg font-medium text-gray-900 mb-4 flex items-center">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium mr-2 ${toolTypeColors[type] || 'bg-gray-100 text-gray-800'}`}>
                      {type.toUpperCase()}
                    </span>
                    {typeTools.length} tools
                  </h2>
                  
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    {typeTools.map((tool) => (
                      <div key={tool.id} className="bg-white border border-gray-200 rounded-lg hover:shadow-md transition-shadow">
                        <div className="p-4">
                          <div className="flex items-start justify-between">
                            <div className="flex-1">
                              <h3 className="text-lg font-medium text-gray-900 font-mono">
                                {tool.name}
                              </h3>
                              <p className="mt-1 text-sm text-gray-600">
                                {extractPurpose(tool.content)}
                              </p>
                              {extractPath(tool.content) && (
                                <p className="mt-1 text-xs text-gray-500 font-mono">
                                  {extractPath(tool.content)}
                                </p>
                              )}
                            </div>
                            <div className="flex items-center space-x-2 ml-4">
                              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${priorityColors[tool.priority]}`}>
                                {tool.priority}
                              </span>
                            </div>
                          </div>
                          
                          {/* Tags */}
                          {tool.tags.length > 0 && (
                            <div className="mt-3 flex flex-wrap gap-1">
                              {tool.tags.slice(0, 4).map((tag) => (
                                <span key={tag} className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-gray-100 text-gray-800">
                                  <Tag className="h-3 w-3 mr-1" />
                                  {tag}
                                </span>
                              ))}
                              {tool.tags.length > 4 && (
                                <span className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-gray-100 text-gray-800">
                                  +{tool.tags.length - 4} more
                                </span>
                              )}
                            </div>
                          )}
                          
                          {/* Action buttons */}
                          <div className="mt-4 flex justify-end">
                            <button
                              onClick={() => {
                                console.log('Opening modal for tool:', tool);
                                setSelectedTool(tool);
                                setShowFullDocs(true);
                              }}
                              className="inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-medium rounded-md text-indigo-700 bg-indigo-100 hover:bg-indigo-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                            >
                              View Full Documentation
                            </button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Full Documentation Modal */}
      {showFullDocs && selectedTool && (() => {
        console.log('Rendering modal for:', selectedTool.name, 'Content length:', selectedTool.content?.length);
        return (
        <div className="fixed inset-0 z-[9999] bg-black bg-opacity-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden" style={{border: '3px solid red'}}>
              {/* Header */}
              <div className="flex items-center justify-between p-6 border-b">
                <h3 className="text-xl font-bold text-gray-900 font-mono">
                  {selectedTool.name}
                </h3>
                <button
                  onClick={() => setShowFullDocs(false)}
                  className="p-2 hover:bg-gray-100 rounded-md"
                >
                  <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              
              {/* Content */}
              <div className="p-6 overflow-y-auto max-h-[60vh]">
                <pre className="whitespace-pre-wrap text-sm text-gray-700 bg-gray-50 p-4 rounded-md">
                  {selectedTool.content}
                </pre>
              </div>
              
              {/* Footer */}
              <div className="px-6 py-4 border-t bg-gray-50">
                <div className="flex items-center justify-between text-sm text-gray-600">
                  <div>
                    <span className="font-medium">Type:</span> {selectedTool.type} |{' '}
                    <span className="font-medium">Priority:</span> {selectedTool.priority}
                  </div>
                  <div>
                    <span className="font-medium">Tags:</span> {selectedTool.tags.join(', ')}
                  </div>
                </div>
              </div>
            </div>
        </div>
        );
      })()}
    </div>
  );
};

export default ToolDocumentation;