import React, { useState, useEffect } from 'react';
import { apiService } from '../services/api';
import { Portfolio as PortfolioType, Holding } from '../types';
import { RefreshCw, TrendingUp, TrendingDown, PieChart } from 'lucide-react';

const Portfolio: React.FC = () => {
  const [portfolio, setPortfolio] = useState<PortfolioType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchPortfolio = async () => {
    try {
      setLoading(true);
      const data = await apiService.getPortfolio();
      setPortfolio(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch portfolio');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPortfolio();
  }, []);

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
    }).format(amount);
  };

  const calculatePnL = (holding: Holding) => {
    // This would need current market price to calculate actual P&L
    // For now, showing the market value
    return holding.market_value;
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

  const totalPnL = portfolio ? portfolio.total_portfolio_value - 1000000 : 0; // Assuming initial cash was 10L
  const totalPnLPercent = totalPnL / 1000000 * 100;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">Portfolio</h1>
        <button
          onClick={fetchPortfolio}
          className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 transition-colors"
        >
          <RefreshCw className="w-4 h-4 mr-2" />
          Refresh
        </button>
      </div>

      {/* Portfolio Summary */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-medium text-gray-600">Total Value</h3>
              <p className="text-2xl font-bold text-gray-900 mt-1">
                {portfolio ? formatCurrency(portfolio.total_portfolio_value) : 'Loading...'}
              </p>
            </div>
            <div className="p-3 bg-blue-100 rounded-full">
              <PieChart className="w-6 h-6 text-blue-600" />
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-medium text-gray-600">Available Cash</h3>
              <p className="text-2xl font-bold text-green-600 mt-1">
                {portfolio ? formatCurrency(portfolio.cash) : 'Loading...'}
              </p>
            </div>
            <div className="p-3 bg-green-100 rounded-full">
              <TrendingUp className="w-6 h-6 text-green-600" />
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-medium text-gray-600">Holdings Value</h3>
              <p className="text-2xl font-bold text-blue-600 mt-1">
                {portfolio ? formatCurrency(portfolio.total_holdings_value) : 'Loading...'}
              </p>
            </div>
            <div className="p-3 bg-blue-100 rounded-full">
              <TrendingUp className="w-6 h-6 text-blue-600" />
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-medium text-gray-600">Total P&L</h3>
              <p className={`text-2xl font-bold mt-1 ${totalPnL >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {formatCurrency(totalPnL)}
              </p>
              <p className={`text-sm ${totalPnL >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {totalPnL >= 0 ? '+' : ''}{totalPnLPercent.toFixed(2)}%
              </p>
            </div>
            <div className={`p-3 rounded-full ${totalPnL >= 0 ? 'bg-green-100' : 'bg-red-100'}`}>
              {totalPnL >= 0 ? (
                <TrendingUp className="w-6 h-6 text-green-600" />
              ) : (
                <TrendingDown className="w-6 h-6 text-red-600" />
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Holdings Table */}
      {portfolio && portfolio.holdings.length > 0 ? (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200">
          <div className="p-6 border-b border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900">
              Holdings ({portfolio.holdings.length})
            </h3>
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
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Allocation
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {portfolio.holdings.map((holding, index) => {
                  const allocation = (holding.market_value / portfolio.total_holdings_value) * 100;
                  return (
                    <tr key={index} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900">
                          {holding.symbol}
                        </div>
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
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        <div className="flex items-center">
                          <div className="w-16 bg-gray-200 rounded-full h-2 mr-2">
                            <div
                              className="bg-blue-600 h-2 rounded-full"
                              style={{ width: `${Math.min(allocation, 100)}%` }}
                            ></div>
                          </div>
                          <span>{allocation.toFixed(1)}%</span>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8 text-center">
          <PieChart className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No Holdings</h3>
          <p className="text-gray-500">
            Start trading to build your portfolio. Your holdings will appear here.
          </p>
        </div>
      )}
    </div>
  );
};

export default Portfolio;