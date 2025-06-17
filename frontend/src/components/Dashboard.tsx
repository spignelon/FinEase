import React, { useState, useEffect } from 'react';
import { apiService } from '../services/api';
import { Portfolio, MarketData } from '../types';
import { TrendingUp, TrendingDown, Wallet, BarChart3, RefreshCw } from 'lucide-react';

const Dashboard: React.FC = () => {
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [marketData, setMarketData] = useState<MarketData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchData = async () => {
    try {
      setLoading(true);
      const [portfolioData, marketDataResponse] = await Promise.all([
        apiService.getPortfolio(),
        apiService.getMarketData(),
      ]);
      setPortfolio(portfolioData);
      setMarketData(marketDataResponse);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
    }).format(amount);
  };

  const formatNumber = (num: number) => {
    return new Intl.NumberFormat('en-IN').format(num);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
        {error}
      </div>
    );
  }

  const niftyData = marketData?.marketState.find(item => item.index === 'NIFTY 50');
  const totalPnL = portfolio ? portfolio.total_portfolio_value - 1000000 : 0; // Assuming initial cash was 10L
  const totalPnLPercent = totalPnL / 1000000 * 100;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        <button
          onClick={fetchData}
          className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 transition-colors"
        >
          <RefreshCw className="w-4 h-4 mr-2" />
          Refresh
        </button>
      </div>

      {/* Market Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-gray-900">NIFTY 50</h3>
              <p className="text-3xl font-bold text-gray-900 mt-2">
                {niftyData ? formatNumber(niftyData.last) : 'N/A'}
              </p>
              {niftyData?.change && (
                <div className={`flex items-center mt-2 ${niftyData.change >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {niftyData.change >= 0 ? <TrendingUp className="w-4 h-4 mr-1" /> : <TrendingDown className="w-4 h-4 mr-1" />}
                  <span className="font-medium">
                    {niftyData.change >= 0 ? '+' : ''}{formatNumber(niftyData.change)} ({niftyData.pChange?.toFixed(2)}%)
                  </span>
                </div>
              )}
            </div>
            <div className="p-3 bg-blue-100 rounded-full">
              <BarChart3 className="w-8 h-8 text-blue-600" />
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-gray-900">Portfolio P&L</h3>
              <p className="text-3xl font-bold text-gray-900 mt-2">
                {formatCurrency(totalPnL)}
              </p>
              <div className={`flex items-center mt-2 ${totalPnL >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {totalPnL >= 0 ? <TrendingUp className="w-4 h-4 mr-1" /> : <TrendingDown className="w-4 h-4 mr-1" />}
                <span className="font-medium">
                  {totalPnL >= 0 ? '+' : ''}{totalPnLPercent.toFixed(2)}%
                </span>
              </div>
            </div>
            <div className="p-3 bg-purple-100 rounded-full">
              <Wallet className="w-8 h-8 text-purple-600" />
            </div>
          </div>
        </div>
      </div>

      {/* Portfolio Summary */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Available Cash</h3>
          <p className="text-2xl font-bold text-green-600">
            {portfolio ? formatCurrency(portfolio.cash) : 'Loading...'}
          </p>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Holdings Value</h3>
          <p className="text-2xl font-bold text-blue-600">
            {portfolio ? formatCurrency(portfolio.total_holdings_value) : 'Loading...'}
          </p>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Total Value</h3>
          <p className="text-2xl font-bold text-gray-900">
            {portfolio ? formatCurrency(portfolio.total_portfolio_value) : 'Loading...'}
          </p>
        </div>
      </div>

      {/* Holdings */}
      {portfolio && portfolio.holdings.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200">
          <div className="p-6 border-b border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900">Current Holdings</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Symbol
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Quantity
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Avg Price
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Market Value
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {portfolio.holdings.map((holding, index) => (
                  <tr key={index}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {holding.symbol}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {holding.quantity}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {formatCurrency(holding.price)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 font-medium">
                      {formatCurrency(holding.market_value)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default Dashboard;