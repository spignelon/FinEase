export interface User {
  user_id: string;
  username: string;
  token: string;
}

export interface Holding {
  symbol: string;
  quantity: number;
  price: number;
  market_value: number;
}

export interface Portfolio {
  cash: number;
  holdings: Holding[];
  total_holdings_value: number;
  total_portfolio_value: number;
  nifty_price: number;
}

export interface Option {
  underlying: string;
  expiryDate: string;
  strikePrice: number;
  optionType: string;
  lastPrice: number;
  formattedSymbol: string;
  change?: number;
  pChange?: number;
  volume?: number;
  openInterest?: number;
}

export interface Trade {
  _id: string;
  user_id: string;
  symbol: string;
  quantity: number;
  price: number;
  order_type: 'buy' | 'sell';
  timestamp: string;
  total_value: number;
}

export interface MarketData {
  _id: string;
  marketState: Array<{
    index: string;
    last: number;
    change?: number;
    pChange?: number;
  }>;
  timestamp: string;
}

export interface TradeRequest {
  symbol: string;
  quantity: number;
  price: number;
  order_type: 'buy' | 'sell';
}

export interface TradeResponse {
  status: 'success' | 'error';
  message: string;
  total_cost?: number;
  transaction_fee?: number;
  trade_id?: string;
}