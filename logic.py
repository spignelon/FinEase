import dataclasses
from typing import Dict, Union, List, Optional
from datetime import datetime
import db

# --- Configuration ---
TRANSACTION_COST_PERCENT = 0.0075  # 0.75% transaction fee

# Define lot sizes for different underlyings
LOT_SIZES = {
    "NIFTY": 75,
    "BANKNIFTY": 25,
    "FINNIFTY": 65,
    "default": 1  # Default lot size for other symbols
}

# --- Custom Exceptions ---
class InsufficientFundsError(Exception):
    """Raised when trying to buy without enough cash."""
    pass

class InsufficientSharesError(Exception):
    """Raised when trying to sell more shares than owned."""
    pass

class InvalidSymbolError(Exception):
    """Raised when the provided symbol is not valid or not found."""
    pass

# --- Data Class for Orders ---
@dataclasses.dataclass
class Order:
    """Represents a buy or sell order."""
    symbol: str
    quantity: int  # Now represents number of lots
    price: float   # Per unit price
    order_type: str  # 'buy' or 'sell'
    user_id: str = None
    timestamp: datetime = None

# Helper function to determine lot size based on symbol
def get_lot_size(symbol):
    """Determine the lot size for a given symbol."""
    if symbol.startswith("NIFTY"):
        return LOT_SIZES["NIFTY"]
    elif symbol.startswith("BANKNIFTY"):
        return LOT_SIZES["BANKNIFTY"]
    elif symbol.startswith("FINNIFTY"):
        return LOT_SIZES["FINNIFTY"]
    return LOT_SIZES["default"]

# --- Portfolio Management ---
class Portfolio:
    """Manages user's assets, including cash and stock holdings."""

    @staticmethod
    def get_portfolio(user_id):
        """Get portfolio for a user from the database."""
        portfolio_data = db.get_portfolio(user_id)
        if not portfolio_data:
            # Create a new portfolio if one doesn't exist
            portfolio_data = db.create_portfolio(user_id)
        
        return {
            "cash": portfolio_data["cash"],
            "holdings": portfolio_data.get("holdings", {}),
            "user_id": user_id
        }
    
    @staticmethod
    def update_holdings(user_id, symbol, quantity):
        """Updates the quantity of a stock in the portfolio."""
        db.update_portfolio_holdings(user_id, symbol, quantity)
    
    @staticmethod
    def update_cash(user_id, cash_change):
        """Updates the cash balance in the portfolio."""
        db.update_portfolio_cash(user_id, cash_change)

# --- Option Chain Utilities ---
class OptionChain:
    """Handles option chain data retrieval and formatting."""
    
    @staticmethod
    def parse_symbol(symbol):
        """
        Parse an option symbol to extract its components.
        
        Args:
            symbol (str): The symbol to parse (e.g., NIFTY26JUN2523050PE)
            
        Returns:
            dict: A dictionary with the parsed components
        """
        return db.parse_option_symbol(symbol)
    
    @staticmethod
    def search_options(search_query):
        """Search for options based on query string."""
        # Get options data from master collection with the search query
        all_options = db.get_options_from_master()
        
        if not all_options:
            return []
        
        search_query = search_query.upper()
        results = []
        
        for option in all_options:
            symbol = option.get("symbol", "")
            
            if search_query in symbol:
                # Add LTP data
                token = option.get("token")
                if token:
                    ltp = db.get_latest_ltp(token)
                    option["lastPrice"] = ltp
                
                results.append(option)
        
        return results[:20]  # Limit results to prevent overload
    
    @staticmethod
    def get_option_by_symbol(symbol):
        """Get option data by symbol."""
        option = db.get_option_with_ltp(symbol)
        
        if not option:
            raise InvalidSymbolError(f"Option not found: {symbol}")
        
        return option

# --- Core Trading Logic ---
class TradingSystem:
    """Handles the execution of trades using paper money."""

    @staticmethod
    def execute_trade(order: Order) -> dict:
        """
        Executes a trade based on the provided order.
        Returns a confirmation message and trade details.
        """
        if not order.timestamp:
            order.timestamp = datetime.now()
            
        if order.order_type.lower() == 'buy':
            return TradingSystem._execute_buy(order)
        elif order.order_type.lower() == 'sell':
            return TradingSystem._execute_sell(order)
        else:
            raise ValueError("Invalid order type. Use 'buy' or 'sell'.")

    @staticmethod
    def _execute_buy(order: Order) -> dict:
        """Executes a buy order."""
        # Get the current portfolio
        portfolio = Portfolio.get_portfolio(order.user_id)
        
        # Get lot size for the symbol
        lot_size = get_lot_size(order.symbol)
        
        # Get current price from LTP if available and price is 0
        if order.price == 0:
            try:
                option_data = db.get_option_with_ltp(order.symbol)
                if option_data and "lastPrice" in option_data and option_data["lastPrice"] is not None:
                    order.price = option_data["lastPrice"]
            except Exception as e:
                print(f"Error getting LTP for {order.symbol}: {e}")
                # Continue with the provided price
        
        # Calculate costs with lot size
        units_per_lot = lot_size
        total_units = order.quantity * units_per_lot
        unit_price = order.price
        total_cost = total_units * unit_price
        transaction_fee = total_cost * TRANSACTION_COST_PERCENT
        total_debit = total_cost + transaction_fee

        if total_debit > portfolio["cash"]:
            raise InsufficientFundsError(
                f"Not enough cash to buy {order.quantity} lots ({total_units} units) of {order.symbol}. "
                f"Required: ₹{total_debit:,.2f}, Available: ₹{portfolio['cash']:,.2f}"
            )

        # Update portfolio
        Portfolio.update_cash(order.user_id, -total_debit)
        Portfolio.update_holdings(order.user_id, order.symbol, order.quantity)
        
        # Record the trade
        trade_record = db.record_trade(
            order.user_id,
            order.symbol,
            order.quantity,
            order.price,
            "buy",
            order.timestamp
        )

        return {
            "status": "success",
            "message": f"Successfully bought {order.quantity} lots ({total_units} units) of {order.symbol} at ₹{order.price:,.2f} per unit.",
            "lot_size": lot_size,
            "total_units": total_units,
            "unit_price": unit_price,
            "total_cost": total_cost,
            "transaction_fee": transaction_fee,
            "total_debit": total_debit,
            "trade_id": str(trade_record["_id"])
        }

    @staticmethod
    def _execute_sell(order: Order) -> dict:
        """Executes a sell order."""
        # Get the current portfolio
        portfolio = Portfolio.get_portfolio(order.user_id)
        holdings = portfolio.get("holdings", {})
        
        if order.symbol not in holdings or holdings[order.symbol] < order.quantity:
            current_lots = holdings.get(order.symbol, 0)
            raise InsufficientSharesError(
                f"Not enough lots to sell. "
                f"Trying to sell: {order.quantity} lots, Owned: {current_lots} lots"
            )

        # Get lot size for the symbol
        lot_size = get_lot_size(order.symbol)
        
        # Get current price from LTP if available and price is 0
        if order.price == 0:
            try:
                option_data = db.get_option_with_ltp(order.symbol)
                if option_data and "lastPrice" in option_data and option_data["lastPrice"] is not None:
                    order.price = option_data["lastPrice"]
            except Exception as e:
                print(f"Error getting LTP for {order.symbol}: {e}")
                # Continue with the provided price
        
        # Calculate proceeds with lot size
        units_per_lot = lot_size
        total_units = order.quantity * units_per_lot
        unit_price = order.price
        total_value = total_units * unit_price
        transaction_fee = total_value * TRANSACTION_COST_PERCENT
        total_credit = total_value - transaction_fee

        # Update portfolio
        Portfolio.update_cash(order.user_id, total_credit)
        Portfolio.update_holdings(order.user_id, order.symbol, -order.quantity)
        
        # Record the trade
        trade_record = db.record_trade(
            order.user_id,
            order.symbol,
            -order.quantity,  # Negative to indicate selling
            order.price,
            "sell",
            order.timestamp
        )

        return {
            "status": "success",
            "message": f"Successfully sold {order.quantity} lots ({total_units} units) of {order.symbol} at ₹{order.price:,.2f} per unit.",
            "lot_size": lot_size,
            "total_units": total_units,
            "unit_price": unit_price,
            "total_value": total_value,
            "transaction_fee": transaction_fee,
            "total_credit": total_credit,
            "trade_id": str(trade_record["_id"])
        }

    @staticmethod
    def get_trade_history(user_id, limit=50):
        """Get the trade history for a user."""
        trades = db.get_user_trades(user_id, limit)
        return trades
