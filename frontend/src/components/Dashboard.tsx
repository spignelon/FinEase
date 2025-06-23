import React, { useState, useEffect } from 'react';
import { apiService } from '../services/api';
import { Portfolio } from '../types';
import { TrendingUp, TrendingDown, Wallet, BarChart3, RefreshCw, X } from 'lucide-react';

const Dashboard: React.FC = () => {
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [niftyData, setNiftyData] = useState<{ 
    price: number; 
    status: string; 
    symbol: string; 
    timestamp: string;
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [exitingPosition, setExitingPosition] = useState<string | null>(null);
  const [tradeMessage, setTradeMessage] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [portfolioData, niftyPriceData] = await Promise.all([
        apiService.getPortfolio(),
        apiService.getNiftyPrice(),
      ]);
      setPortfolio(portfolioData);
      setNiftyData(niftyPriceData);
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

  const exitPosition = async (symbol: string, quantity: number, price: number, positionType: string) => {
    try {
      setExitingPosition(symbol);
      setTradeMessage(null);
      
      // For long positions we need to sell, for short positions we need to buy
      const orderType = positionType === 'long' ? 'sell' : 'buy';
      
      // We use the absolute value of quantity because short positions have negative quantities in display
      const absoluteQuantity = Math.abs(quantity);
      
      const result = await apiService.executeTrade({
        symbol,
        quantity: absoluteQuantity,
        price, // Use current price for exit
        order_type: orderType,
      });
      
      if (result.status === 'success') {
        setTradeMessage({
          type: 'success',
          message: `Successfully exited ${absoluteQuantity} lots of ${symbol}`
        });
        // Refresh data to update portfolio
        fetchData();
      } else {
        setTradeMessage({
          type: 'error',
          message: result.message || 'Failed to exit position'
        });
      }
    } catch (err) {
      setTradeMessage({
        type: 'error',
        message: err instanceof Error ? err.message : 'Failed to exit position'
      });
    } finally {
      setExitingPosition(null);
    }
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
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        <button
          onClick={fetchData}
          className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 transition-colors"
        >
          <RefreshCw className="w-4 h-4 mr-2" />
          Refresh
        </button>
      </div>

      {/* Market Overview - Simplified to only show the price without change data */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-gray-900">NIFTY 50</h3>
              <p className="text-3xl font-bold text-gray-900 mt-2">
                {niftyData ? formatNumber(niftyData.price) : 'N/A'}
              </p>
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

      {tradeMessage && (
        <div className={`p-4 rounded-lg ${
          tradeMessage.type === 'success' 
            ? 'bg-green-50 border border-green-200 text-green-700' 
            : 'bg-red-50 border border-red-200 text-red-700'
        }`}>
          {tradeMessage.message}
        </div>
      )}

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
                    LTP
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Market Value
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Action
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
                      {typeof holding.price === 'number' ? formatCurrency(holding.price) : holding.price}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {/* For short positions with entry_price, current_price represents LTP */}
                      {holding.position_type === 'short' && holding.current_price ? 
                        formatCurrency(holding.current_price) : 
                        (typeof holding.price === 'number' ? formatCurrency(holding.price) : 'N/A')}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 font-medium">
                      {typeof holding.market_value === 'number' ? formatCurrency(holding.market_value) : 'N/A'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      <button
                        onClick={() => {
                          // Determine the current price to use for the exit order
                          const currentPrice = holding.position_type === 'short' && holding.current_price
                            ? holding.current_price
                            : (typeof holding.price === 'number' ? holding.price : 0);
                            
                          exitPosition(
                            holding.symbol, 
                            holding.quantity, 
                            currentPrice,
                            holding.position_type || 'long'
                          );
                        }}
                        disabled={exitingPosition === holding.symbol}
                        className={`inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-medium rounded-md text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 transition-colors ${
                          exitingPosition === holding.symbol ? 'opacity-50 cursor-not-allowed' : ''
                        }`}
                      >
                        {exitingPosition === holding.symbol ? (
                          <>
                            <RefreshCw className="animate-spin -ml-0.5 mr-1 h-3 w-3" />
                            Exiting...
                          </>
                        ) : (
                          <>
                            <X className="-ml-0.5 mr-1 h-3 w-3" />
                            Exit
                          </>
                        )}
                      </button>
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