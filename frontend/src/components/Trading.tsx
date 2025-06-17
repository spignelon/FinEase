import React, { useState, useEffect } from 'react';
import { apiService } from '../services/api';
import { Option } from '../types';
import { Search, TrendingUp, TrendingDown, RefreshCw } from 'lucide-react';

const Trading: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [options, setOptions] = useState<Option[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedOption, setSelectedOption] = useState<Option | null>(null);
  const [tradeForm, setTradeForm] = useState({
    quantity: 1,
    orderType: 'buy' as 'buy' | 'sell',
  });
  const [tradeLoading, setTradeLoading] = useState(false);
  const [tradeMessage, setTradeMessage] = useState('');

  const searchOptions = async () => {
    if (searchQuery.length < 2) return;
    
    setLoading(true);
    try {
      const response = await apiService.searchOptions(searchQuery);
      setOptions(response.options);
    } catch (error) {
      console.error('Search failed:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadOptionChain = async () => {
    setLoading(true);
    try {
      const response = await apiService.getOptionChain();
      setOptions(response.options.slice(0, 20)); // Show first 20 options
    } catch (error) {
      console.error('Failed to load option chain:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadOptionChain();
  }, []);

  useEffect(() => {
    const timeoutId = setTimeout(() => {
      if (searchQuery.length >= 2) {
        searchOptions();
      } else if (searchQuery.length === 0) {
        loadOptionChain();
      }
    }, 300);

    return () => clearTimeout(timeoutId);
  }, [searchQuery]);

  const handleTrade = async () => {
    if (!selectedOption) return;

    setTradeLoading(true);
    setTradeMessage('');
    
    try {
      const response = await apiService.executeTrade({
        symbol: selectedOption.formattedSymbol,
        quantity: tradeForm.quantity,
        price: selectedOption.lastPrice,
        order_type: tradeForm.orderType,
      });

      if (response.status === 'success') {
        setTradeMessage(response.message);
        setSelectedOption(null);
        setTradeForm({ quantity: 1, orderType: 'buy' });
      } else {
        setTradeMessage(response.message);
      }
    } catch (error) {
      setTradeMessage(error instanceof Error ? error.message : 'Trade failed');
    } finally {
      setTradeLoading(false);
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
    }).format(amount);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">Options Trading</h1>
        <button
          onClick={loadOptionChain}
          className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 transition-colors"
        >
          <RefreshCw className="w-4 h-4 mr-2" />
          Refresh
        </button>
      </div>

      {/* Search */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
          <input
            type="text"
            placeholder="Search options (e.g., NIFTY, 22800, CE)..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Options List */}
        <div className="lg:col-span-2 bg-white rounded-xl shadow-sm border border-gray-200">
          <div className="p-6 border-b border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900">
              {searchQuery ? `Search Results (${options.length})` : 'NIFTY Options'}
            </h3>
          </div>
          
          {loading ? (
            <div className="flex items-center justify-center h-32">
              <RefreshCw className="w-6 h-6 animate-spin text-blue-600" />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Symbol
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Strike
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Type
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      LTP
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Change
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Action
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {options.map((option, index) => (
                    <tr key={index} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {option.formattedSymbol}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {option.strikePrice}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                          option.optionType === 'CE' 
                            ? 'bg-green-100 text-green-800' 
                            : 'bg-red-100 text-red-800'
                        }`}>
                          {option.optionType}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 font-medium">
                        {formatCurrency(option.lastPrice)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        {option.change && (
                          <div className={`flex items-center ${option.change >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                            {option.change >= 0 ? <TrendingUp className="w-4 h-4 mr-1" /> : <TrendingDown className="w-4 h-4 mr-1" />}
                            <span>{option.change >= 0 ? '+' : ''}{option.change?.toFixed(2)}</span>
                          </div>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        <button
                          onClick={() => setSelectedOption(option)}
                          className="bg-blue-600 text-white px-3 py-1 rounded text-xs hover:bg-blue-700 transition-colors"
                        >
                          Trade
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Trade Panel */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Place Order</h3>
          
          {selectedOption ? (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Selected Option</label>
                <div className="bg-gray-50 p-3 rounded-lg">
                  <p className="font-medium text-sm">{selectedOption.formattedSymbol}</p>
                  <p className="text-sm text-gray-600">LTP: {formatCurrency(selectedOption.lastPrice)}</p>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Order Type</label>
                <div className="flex space-x-2">
                  <button
                    onClick={() => setTradeForm({ ...tradeForm, orderType: 'buy' })}
                    className={`flex-1 py-2 px-4 rounded-lg text-sm font-medium transition-colors ${
                      tradeForm.orderType === 'buy'
                        ? 'bg-green-600 text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    Buy
                  </button>
                  <button
                    onClick={() => setTradeForm({ ...tradeForm, orderType: 'sell' })}
                    className={`flex-1 py-2 px-4 rounded-lg text-sm font-medium transition-colors ${
                      tradeForm.orderType === 'sell'
                        ? 'bg-red-600 text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    Sell
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Quantity</label>
                <input
                  type="number"
                  min="1"
                  value={tradeForm.quantity}
                  onChange={(e) => setTradeForm({ ...tradeForm, quantity: parseInt(e.target.value) || 1 })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              <div className="bg-gray-50 p-3 rounded-lg">
                <div className="flex justify-between text-sm">
                  <span>Total Value:</span>
                  <span className="font-medium">
                    {formatCurrency(selectedOption.lastPrice * tradeForm.quantity)}
                  </span>
                </div>
              </div>

              <button
                onClick={handleTrade}
                disabled={tradeLoading}
                className={`w-full py-3 rounded-lg font-medium transition-colors ${
                  tradeForm.orderType === 'buy'
                    ? 'bg-green-600 hover:bg-green-700 text-white'
                    : 'bg-red-600 hover:bg-red-700 text-white'
                } disabled:opacity-50 disabled:cursor-not-allowed`}
              >
                {tradeLoading ? 'Executing...' : `${tradeForm.orderType === 'buy' ? 'Buy' : 'Sell'} ${tradeForm.quantity} Lot${tradeForm.quantity > 1 ? 's' : ''}`}
              </button>

              {tradeMessage && (
                <div className={`p-3 rounded-lg text-sm ${
                  tradeMessage.includes('success') || tradeMessage.includes('Successfully')
                    ? 'bg-green-50 text-green-700 border border-green-200'
                    : 'bg-red-50 text-red-700 border border-red-200'
                }`}>
                  {tradeMessage}
                </div>
              )}
            </div>
          ) : (
            <p className="text-gray-500 text-center py-8">Select an option to trade</p>
          )}
        </div>
      </div>
    </div>
  );
};

export default Trading;