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
  const [selectedIdc, setSelectedIdc] = useState('');
  const [selectedCompetitor, setSelectedCompetitor] = useState('');
  const [matchingLoading, setMatchingLoading] = useState(false);
  const { toast } = useToast();

  const fetchMatches = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/price-monitor/product-matching/matches');
      if (response.ok) {
        const data = await response.json();
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
      const [idcResponse, compResponse] = await Promise.all([
        fetch('/api/price-monitor/shopify-sync/idc-products?limit=200'),
        fetch('/api/price-monitor/competitors/products?limit=200')
      ]);
      
      if (idcResponse.ok && compResponse.ok) {
        const idcData = await idcResponse.json();
        const compData = await compResponse.json();
        setIdcProducts(idcData.products || []);
        setCompetitorProducts(compData.products || []);
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

      {/* Manual Match Modal */}
      {showManualMatch && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <h3 className="text-lg font-semibold mb-4">Create Manual Match</h3>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
              <div>
                <label className="block text-sm font-medium mb-2">IDC Product</label>
                <select 
                  value={selectedIdc} 
                  onChange={(e) => setSelectedIdc(e.target.value)}
                  className="w-full p-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                >
                  <option value="">Select IDC Product</option>
                  {idcProducts.map(product => (
                    <option key={product.id} value={product.id}>
                      {product.title} - ${product.price}
                    </option>
                  ))}
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-2">Competitor Product</label>
                <select 
                  value={selectedCompetitor} 
                  onChange={(e) => setSelectedCompetitor(e.target.value)}
                  className="w-full p-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                >
                  <option value="">Select Competitor Product</option>
                  {competitorProducts.map(product => (
                    <option key={product.id} value={product.id}>
                      {product.title} - ${product.price} ({product.competitor?.name})
                    </option>
                  ))}
                </select>
              </div>
            </div>
            
            <div className="flex justify-end gap-2">
              <Button 
                onClick={() => setShowManualMatch(false)}
                className="bg-gray-500 hover:bg-gray-600 text-white"
              >
                Cancel
              </Button>
              <Button 
                onClick={createManualMatch}
                disabled={matchingLoading}
                className="bg-blue-600 hover:bg-blue-700 text-white"
              >
                {matchingLoading ? 'Creating...' : 'Create Match'}
              </Button>
            </div>
          </div>
        </div>
      )}

      {matches.length > 0 ? (
        <div className="bg-white dark:bg-gray-800 shadow-sm border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
          {/* Mobile Card View */}
          <div className="block lg:hidden">
            {matches.map((match) => (
              <div key={match.id} className="border-b border-gray-200 dark:border-gray-700 p-4">
                <div className="flex justify-between items-start mb-2">
                  <div className="font-medium text-gray-900 dark:text-white text-sm">
                    {match.idc_product?.title}
                  </div>
                  <Badge color={
                    match.confidence_level === 'high' ? 'green' : 
                    match.confidence_level === 'medium' ? 'yellow' : 'gray'
                  }>
                    {Math.round(match.overall_score * 100)}%
                  </Badge>
                </div>
                <div className="text-sm text-gray-500 dark:text-gray-400 mb-2">
                  → {match.competitor_product?.title}
                </div>
                <div className="flex justify-between items-center">
                  <div className="text-sm">
                    <span className="text-gray-600 dark:text-gray-400">Price: </span>
                    <span className="font-medium">${match.idc_product?.price}</span>
                    <span className="mx-2">vs</span>
                    <span className="font-medium">${match.competitor_product?.price}</span>
                  </div>
                  <Button 
                    size="sm" 
                    onClick={() => deleteMatch(match.id)}
                    className="bg-red-600 hover:bg-red-700 text-white"
                  >
                    Delete
                  </Button>
                </div>
              </div>
            ))}
          </div>

          {/* Desktop Table View */}
          <div className="hidden lg:block">
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
                    Match Score
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Prices
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                {matches.map((match) => (
                  <tr key={match.id}>
                    <td className="px-6 py-4 text-sm font-medium text-gray-900 dark:text-white">
                      <div className="max-w-xs truncate">
                        {match.idc_product?.title}
                      </div>
                      <div className="text-xs text-gray-500 dark:text-gray-400">
                        {match.idc_product?.vendor}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500 dark:text-gray-400">
                      <div className="max-w-xs truncate">
                        {match.competitor_product?.title}
                      </div>
                      <div className="text-xs text-gray-500 dark:text-gray-400">
                        {match.competitor_product?.competitor?.name}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <Badge color={
                        match.confidence_level === 'high' ? 'green' : 
                        match.confidence_level === 'medium' ? 'yellow' : 'gray'
                      }>
                        {Math.round(match.overall_score * 100)}%
                      </Badge>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <div>${match.idc_product?.price}</div>
                      <div className="text-xs text-gray-500">vs ${match.competitor_product?.price}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                      <Button 
                        size="sm" 
                        onClick={() => deleteMatch(match.id)}
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
        </div>
      ) : (
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-12 text-center">
          <div className="text-gray-500 dark:text-gray-400">
            <h3 className="text-lg font-medium mb-2">No product matches found</h3>
            <p className="mb-4">Product matches will appear here once competitor data is scraped and processed.</p>
            <Button 
              onClick={() => console.log('Run product matching')}
              className="bg-blue-600 hover:bg-blue-700 text-white"
            >
              Run Product Matching
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}