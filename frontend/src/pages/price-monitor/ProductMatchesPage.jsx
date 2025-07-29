import React, { useState, useEffect } from 'react';
import { Button } from '@common/button';
import { Badge } from '@common/badge';
import { Heading } from '@common/heading';
import { useToast } from '@common/toast';

export default function ProductMatchesPage() {
  const [matches, setMatches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showManualMatch, setShowManualMatch] = useState(false);
  const [idcProducts, setIdcProducts] = useState([]);
  const [competitorProducts, setCompetitorProducts] = useState([]);
  const [competitors, setCompetitors] = useState([]);
  const [selectedIdc, setSelectedIdc] = useState('');
  const [selectedCompetitor, setSelectedCompetitor] = useState('');
  const [selectedCompetitorFilter, setSelectedCompetitorFilter] = useState('');
  const [idcSearchTerm, setIdcSearchTerm] = useState('');
  const [competitorSearchTerm, setCompetitorSearchTerm] = useState('');
  const [matchingLoading, setMatchingLoading] = useState(false);
  const [previewSimilarity, setPreviewSimilarity] = useState(null);
  const { toast } = useToast();

  const fetchMatches = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/price-monitor/product-matching/matches');
      if (response.ok) {
        const data = await response.json();
        // API now handles sorting with manual matches pinned to top
        setMatches(data.matches || []);
      } else {
        toast.error('Failed to load product matches');
      }
    } catch (error) {
      console.error('Error fetching matches:', error);
      toast.error('Error loading matches');
    } finally {
      setLoading(false);
    }
  };

  const fetchProductsForMatching = async () => {
    try {
      const [idcResponse, compResponse, competitorsResponse] = await Promise.all([
        fetch('/api/price-monitor/shopify-sync/idc-products?limit=200'),
        fetch('/api/price-monitor/competitors/products?limit=500'),
        fetch('/api/price-monitor/competitors')
      ]);
      
      if (idcResponse.ok && compResponse.ok && competitorsResponse.ok) {
        const idcData = await idcResponse.json();
        const compData = await compResponse.json();
        const competitorsData = await competitorsResponse.json();
        
        setIdcProducts(idcData.products || []);
        setCompetitorProducts(compData.products || []);
        setCompetitors(competitorsData.competitors || []);
      }
    } catch (error) {
      console.error('Error fetching products:', error);
      toast.error('Failed to load products for matching');
    }
  };

  const createManualMatch = async () => {
    if (!selectedIdc || !selectedCompetitor) {
      toast.error('Please select both products to match');
      return;
    }

    try {
      setMatchingLoading(true);
      const response = await fetch('/api/price-monitor/product-matching/manual-match', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          idc_product_id: selectedIdc,
          competitor_product_id: selectedCompetitor
        })
      });

      if (response.ok) {
        toast.success('Manual match created successfully');
        setShowManualMatch(false);
        setSelectedIdc('');
        setSelectedCompetitor('');
        fetchMatches();
      } else {
        toast.error('Failed to create manual match');
      }
    } catch (error) {
      console.error('Error creating manual match:', error);
      toast.error('Error creating manual match');
    } finally {
      setMatchingLoading(false);
    }
  };

  const deleteMatch = async (matchId) => {
    try {
      const response = await fetch(`/api/price-monitor/product-matching/matches/${matchId}`, {
        method: 'DELETE'
      });

      if (response.ok) {
        toast.success('Match deleted successfully');
        fetchMatches();
      } else {
        toast.error('Failed to delete match');
      }
    } catch (error) {
      console.error('Error deleting match:', error);
      toast.error('Error deleting match');
    }
  };

  // Filter and search functions
  const filteredIdcProducts = idcProducts.filter(product =>
    product.title?.toLowerCase().includes(idcSearchTerm.toLowerCase()) ||
    product.vendor?.toLowerCase().includes(idcSearchTerm.toLowerCase()) ||
    (product.sku && product.sku.toLowerCase().includes(idcSearchTerm.toLowerCase()))
  );

  const filteredCompetitorProducts = competitorProducts.filter(product => {
    const matchesSearch = product.title?.toLowerCase().includes(competitorSearchTerm.toLowerCase()) ||
      (product.vendor && product.vendor.toLowerCase().includes(competitorSearchTerm.toLowerCase())) ||
      (product.sku && product.sku.toLowerCase().includes(competitorSearchTerm.toLowerCase()));
    
    const matchesCompetitor = !selectedCompetitorFilter || product.competitor_id === selectedCompetitorFilter;
    
    return matchesSearch && matchesCompetitor;
  });

  const getSelectedIdcProduct = () => idcProducts.find(p => p.id === selectedIdc);
  const getSelectedCompetitorProduct = () => competitorProducts.find(p => p.id === selectedCompetitor);
  const getCompetitorName = (competitorId) => competitors.find(c => c.id === competitorId)?.name || 'Unknown';

  useEffect(() => {
    fetchMatches();
  }, []);

  return (
    <div className="p-4 md:p-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-6 gap-4">
        <div>
          <Heading level="1">Product Matches</Heading>
          <p className="mt-2 text-gray-600 dark:text-gray-400">
            View and manage product matches between IDC and competitors
          </p>
        </div>
        <div className="flex flex-col sm:flex-row gap-2">
          <Button 
            onClick={() => {
              setShowManualMatch(true);
              fetchProductsForMatching();
            }}
            className="bg-green-600 hover:bg-green-700 text-white"
          >
            Create Manual Match
          </Button>
          <Button 
            onClick={fetchMatches}
            disabled={loading}
            className="bg-blue-600 hover:bg-blue-700 text-white"
          >
            {loading ? 'Loading...' : 'Refresh'}
          </Button>
        </div>
      </div>

      {/* Enhanced Manual Match Modal */}
      {showManualMatch && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-gray-800 rounded-lg w-full max-w-6xl max-h-[95vh] overflow-hidden flex flex-col">
            {/* Header */}
            <div className="p-6 border-b border-gray-200 dark:border-gray-700">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold">Create Manual Product Match</h3>
                <button
                  onClick={() => {
                    setShowManualMatch(false);
                    setSelectedIdc('');
                    setSelectedCompetitor('');
                    setIdcSearchTerm('');
                    setCompetitorSearchTerm('');
                    setSelectedCompetitorFilter('');
                    setPreviewSimilarity(null);
                  }}
                  className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                >
                  ✕
                </button>
              </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-hidden flex">
              {/* Left Panel - IDC Products */}
              <div className="w-1/3 border-r border-gray-200 dark:border-gray-700 flex flex-col">
                <div className="p-4 border-b border-gray-200 dark:border-gray-700">
                  <h4 className="font-medium mb-2">IDC Products</h4>
                  <input
                    type="text"
                    placeholder="Search IDC products..."
                    value={idcSearchTerm}
                    onChange={(e) => setIdcSearchTerm(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
                  />
                </div>
                <div className="flex-1 overflow-y-auto p-2">
                  {filteredIdcProducts.slice(0, 50).map((product) => (
                    <div
                      key={product.id}
                      onClick={() => setSelectedIdc(product.id)}
                      className={`p-3 mb-2 rounded-lg cursor-pointer border transition-colors ${
                        selectedIdc === product.id
                          ? 'bg-blue-50 border-blue-300 dark:bg-blue-900/20 dark:border-blue-600'
                          : 'bg-gray-50 border-gray-200 hover:bg-gray-100 dark:bg-gray-700 dark:border-gray-600 dark:hover:bg-gray-600'
                      }`}
                    >
                      <div className="font-medium text-sm truncate">{product.title}</div>
                      <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                        {product.vendor} • ${product.price} • {product.sku}
                      </div>
                    </div>
                  ))}
                  {filteredIdcProducts.length > 50 && (
                    <div className="text-center text-sm text-gray-500 p-2">
                      Showing first 50 results. Use search to narrow down.
                    </div>
                  )}
                </div>
              </div>

              {/* Middle Panel - Preview */}
              <div className="w-1/3 border-r border-gray-200 dark:border-gray-700 flex flex-col">
                <div className="p-4 border-b border-gray-200 dark:border-gray-700">
                  <h4 className="font-medium">Match Preview</h4>
                </div>
                <div className="flex-1 overflow-y-auto p-4">
                  {selectedIdc && selectedCompetitor ? (
                    <div className="space-y-4">
                      {/* IDC Product Preview */}
                      <div className="bg-blue-50 dark:bg-blue-900/20 p-3 rounded-lg">
                        <div className="text-sm font-medium text-blue-800 dark:text-blue-300 mb-1">IDC Product</div>
                        <div className="font-medium">{getSelectedIdcProduct()?.title}</div>
                        <div className="text-sm text-gray-600 dark:text-gray-400">
                          {getSelectedIdcProduct()?.vendor} • ${getSelectedIdcProduct()?.price}
                        </div>
                      </div>

                      {/* VS Indicator */}
                      <div className="text-center text-gray-400">↕ VS ↕</div>

                      {/* Competitor Product Preview */}
                      <div className="bg-orange-50 dark:bg-orange-900/20 p-3 rounded-lg">
                        <div className="text-sm font-medium text-orange-800 dark:text-orange-300 mb-1">
                          Competitor Product ({getSelectedCompetitorProduct()?.competitor?.name || 'Unknown'})
                        </div>
                        <div className="font-medium">{getSelectedCompetitorProduct()?.title}</div>
                        <div className="text-sm text-gray-600 dark:text-gray-400">
                          {getSelectedCompetitorProduct()?.vendor} • ${getSelectedCompetitorProduct()?.price}
                        </div>
                      </div>

                      {/* Create Match Button */}
                      <div className="pt-4">
                        <Button
                          onClick={createManualMatch}
                          disabled={matchingLoading}
                          className="w-full bg-green-600 hover:bg-green-700 text-white"
                        >
                          {matchingLoading ? 'Creating Match...' : 'Create Manual Match'}
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <div className="text-center text-gray-500 dark:text-gray-400 py-8">
                      Select products from both sides to preview the match
                    </div>
                  )}
                </div>
              </div>

              {/* Right Panel - Competitor Products */}
              <div className="w-1/3 flex flex-col">
                <div className="p-4 border-b border-gray-200 dark:border-gray-700">
                  <h4 className="font-medium mb-2">Competitor Products</h4>
                  
                  {/* Competitor Filter */}
                  <select
                    value={selectedCompetitorFilter}
                    onChange={(e) => setSelectedCompetitorFilter(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm mb-2 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
                  >
                    <option value="">All Competitors</option>
                    {competitors.map((competitor) => (
                      <option key={competitor.id} value={competitor.id}>
                        {competitor.name} ({competitor.domain})
                      </option>
                    ))}
                  </select>

                  {/* Search */}
                  <input
                    type="text"
                    placeholder="Search competitor products..."
                    value={competitorSearchTerm}
                    onChange={(e) => setCompetitorSearchTerm(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
                  />
                </div>
                <div className="flex-1 overflow-y-auto p-2">
                  {filteredCompetitorProducts.slice(0, 50).map((product) => (
                    <div
                      key={product.id}
                      onClick={() => setSelectedCompetitor(product.id)}
                      className={`p-3 mb-2 rounded-lg cursor-pointer border transition-colors ${
                        selectedCompetitor === product.id
                          ? 'bg-orange-50 border-orange-300 dark:bg-orange-900/20 dark:border-orange-600'
                          : 'bg-gray-50 border-gray-200 hover:bg-gray-100 dark:bg-gray-700 dark:border-gray-600 dark:hover:bg-gray-600'
                      }`}
                    >
                      <div className="font-medium text-sm truncate">{product.title}</div>
                      <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                        <div>{product.competitor?.name || 'Unknown'}</div>
                        <div>{product.vendor} • ${product.price} • {product.sku}</div>
                      </div>
                    </div>
                  ))}
                  {filteredCompetitorProducts.length > 50 && (
                    <div className="text-center text-sm text-gray-500 p-2">
                      Showing first 50 results. Use search to narrow down.
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Existing matches table - need to continue from here... */}
      {loading ? (
        <div className="flex items-center justify-center min-h-[400px]">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          <div className="ml-4 text-gray-500 dark:text-gray-400">Loading matches...</div>
        </div>
      ) : matches.length > 0 ? (
        <div className="bg-white dark:bg-gray-800 shadow-sm border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead className="bg-gray-50 dark:bg-gray-700">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  IDC Product
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Competitor Product
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Confidence
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Type
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
              {matches.map((match) => (
                <tr key={match.id}>
                  <td className="px-6 py-4 text-sm">
                    <div className="font-medium text-gray-900 dark:text-white">
                      {match.idc_product?.title || 'Unknown Product'}
                    </div>
                    <div className="text-gray-500 dark:text-gray-400 text-xs">
                      {match.idc_product?.vendor} • ${match.idc_product?.price} • {match.idc_product?.sku}
                    </div>
                  </td>
                  <td className="px-6 py-4 text-sm">
                    <div className="font-medium text-gray-900 dark:text-white">
                      {match.competitor_product?.title || 'Unknown Product'}
                    </div>
                    <div className="text-gray-500 dark:text-gray-400 text-xs">
                      <div className="font-medium text-orange-600">
                        {match.competitor_product?.competitor?.name || 'Unknown'}
                      </div>
                      <div>{match.competitor_product?.vendor} • ${match.competitor_product?.price}</div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center gap-2">
                      <Badge color={
                        match.is_manual_match ? 'green' :
                        match.confidence_level === 'high' ? 'green' :
                        match.confidence_level === 'medium' ? 'yellow' :
                        match.confidence_level === 'low' ? 'orange' : 'red'
                      }>
                        {match.is_manual_match ? 'manual (100.0%)' : `${match.confidence_level} (${(match.overall_score * 100).toFixed(1)}%)`}
                      </Badge>
                      {match.is_manual_match && (
                        <span className="text-xs text-blue-600 dark:text-blue-400 font-medium">📌</span>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <Badge color={match.is_manual_match ? 'blue' : 'gray'}>
                      {match.is_manual_match ? 'Manual' : 'Auto'}
                    </Badge>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    <Button
                      onClick={() => deleteMatch(match.id)}
                      size="sm"
                      className="bg-red-600 hover:bg-red-700 text-white"
                    >
                      Delete
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-12 text-center">
          <div className="text-gray-500 dark:text-gray-400">
            <h3 className="text-lg font-medium mb-2">No product matches found</h3>
            <p className="mb-4">
              Create manual matches or run automatic matching to see results here.
            </p>
            <Button 
              onClick={() => {
                setShowManualMatch(true);
                fetchProductsForMatching();
              }}
              className="bg-green-600 hover:bg-green-700 text-white"
            >
              Create Manual Match
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}