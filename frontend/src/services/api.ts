import { User, Portfolio, Option, Trade, TradeRequest, TradeResponse } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:3000';

class ApiService {
  private getAuthHeaders(): HeadersInit {
    const token = localStorage.getItem('token');
    return {
      'Content-Type': 'application/json',
      ...(token && { 'Authorization': token }),
    };
  }

  async register(username: string, password: string, email: string): Promise<User> {
    const response = await fetch(`${API_BASE_URL}/api/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password, email }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message || 'Registration failed');
    }

    const data = await response.json();
    localStorage.setItem('token', data.token);
    return data;
  }

  async login(username: string, password: string): Promise<User> {
    const response = await fetch(`${API_BASE_URL}/api/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message || 'Login failed');
    }

    const data = await response.json();
    localStorage.setItem('token', data.token);
    return data;
  }

  async getPortfolio(): Promise<Portfolio> {
    const response = await fetch(`${API_BASE_URL}/api/portfolio`, {
      headers: this.getAuthHeaders(),
    });

    if (!response.ok) {
      throw new Error('Failed to fetch portfolio');
    }

    return response.json();
  }

  async getOptionChain(symbol = 'NIFTY', expiry?: string): Promise<{ options: Option[]; timestamp: string; count: number }> {
    const params = new URLSearchParams();
    if (symbol) params.append('symbol', symbol);
    if (expiry) params.append('expiry', expiry);

    const response = await fetch(`${API_BASE_URL}/api/option_chain?${params}`);
    
    if (!response.ok) {
      throw new Error('Failed to fetch option chain');
    }

    return response.json();
  }

  async searchOptions(query: string): Promise<{ options: Option[]; count: number }> {
    const response = await fetch(`${API_BASE_URL}/api/options/search?q=${encodeURIComponent(query)}`);
    
    if (!response.ok) {
      throw new Error('Failed to search options');
    }

    return response.json();
  }

  async executeTrade(trade: TradeRequest): Promise<TradeResponse> {
    const response = await fetch(`${API_BASE_URL}/api/trade`, {
      method: 'POST',
      headers: this.getAuthHeaders(),
      body: JSON.stringify(trade),
    });

    const data = await response.json();
    
    if (!response.ok && data.status === 'error') {
      throw new Error(data.message);
    }

    return data;
  }

  async getTradeHistory(limit = 50): Promise<{ trades: Trade[]; count: number }> {
    const response = await fetch(`${API_BASE_URL}/api/trades?limit=${limit}`, {
      headers: this.getAuthHeaders(),
    });

    if (!response.ok) {
      throw new Error('Failed to fetch trade history');
    }

    return response.json();
  }

  async getNiftyPrice(): Promise<{ 
    price: number; 
    status: string; 
    symbol: string; 
    timestamp: string;
  }> {
    const response = await fetch(`${API_BASE_URL}/api/nifty_price`);
    
    if (!response.ok) {
      throw new Error('Failed to fetch Nifty price');
    }

    return response.json();
  }

  logout(): void {
    localStorage.removeItem('token');
  }
}

export const apiService = new ApiService();