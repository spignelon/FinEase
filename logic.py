import dataclasses
from typing import Dict, Union, List, Optional
from datetime import datetime
import db

# --- Configuration ---
TRANSACTION_COST_PERCENT = 0.0075  # 0.75% transaction fee

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
    quantity: int
    price: float
    order_type: str  # 'buy' or 'sell'
    user_id: str = None
    timestamp: datetime = None

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
    def format_symbol(underlying, expiry_date, strike_price, option_type):
        """Format the symbol in the standard way: NIFTY 19JUN25 22800 CE"""
        # Convert expiry_date from "19-06-2025" to "19JUN25"
        date_parts = expiry_date.split("-")
        if len(date_parts) == 3:
            day, month, year = date_parts
            # Convert month number to abbreviated month name
            month_names = {
                "01": "JAN", "02": "FEB", "03": "MAR", "04": "APR", "05": "MAY", "06": "JUN",
                "07": "JUL", "08": "AUG", "09": "SEP", "10": "OCT", "11": "NOV", "12": "DEC"
            }
            month_name = month_names.get(month, month)
            formatted_expiry = f"{day}{month_name}{year[-2:]}"
            return f"{underlying} {formatted_expiry} {strike_price} {option_type}"
        return f"{underlying} {expiry_date} {strike_price} {option_type}"
    
    @staticmethod
    def search_options(search_query):
        """Search for options based on query string."""
        # Get the latest option chain
        latest_options = db.get_latest_option_chain()
        
        if not latest_options:
            return []
        
        search_query = search_query.upper()
        results = []
        
        for option in latest_options:
            formatted_symbol = OptionChain.format_symbol(
                option["underlying"],
                option["expiryDate"],
                option["strikePrice"],
                option["optionType"]
            )
            
            if search_query in formatted_symbol:
                option["formattedSymbol"] = formatted_symbol
                results.append(option)
        
        return results[:20]  # Limit results to prevent overload
    
    @staticmethod
    def get_option_by_symbol(symbol):
        """Get option data by formatted symbol."""
        # Parse the symbol: NIFTY 19JUN25 22800 CE
        parts = symbol.split()
        if len(parts) != 4:
            raise InvalidSymbolError(f"Invalid symbol format: {symbol}")
        
        underlying, expiry, strike, option_type = parts
        
        # Convert expiry from "19JUN25" back to "19-06-2025"
        day = expiry[:2]
        month_str = expiry[2:5]
        year_short = expiry[5:]
        
        month_dict = {
            "JAN": "01", "FEB": "02", "MAR": "03", "APR": "04", "MAY": "05", "JUN": "06",
            "JUL": "07", "AUG": "08", "SEP": "09", "OCT": "10", "NOV": "11", "DEC": "12"
        }
        month = month_dict.get(month_str.upper(), "01")
        
        formatted_expiry = f"{day}-{month}-20{year_short}"
        
        # Query the database
        query = {
            "underlying": underlying,
            "expiryDate": formatted_expiry,
            "strikePrice": float(strike),
            "optionType": option_type
        }
        
        latest_option = db.option_chain_collection.find_one(
            query,
            sort=[("timestamp", -1)]
        )
        
        if not latest_option:
            raise InvalidSymbolError(f"Option not found: {symbol}")
        
        return latest_option

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
        
        # Calculate costs
        total_cost = order.quantity * order.price
        transaction_fee = total_cost * TRANSACTION_COST_PERCENT
        total_debit = total_cost + transaction_fee

        if total_debit > portfolio["cash"]:
            raise InsufficientFundsError(
                f"Not enough cash to buy {order.quantity} of {order.symbol}. "
                f"Required: ${total_debit:,.2f}, Available: ${portfolio['cash']:,.2f}"
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
            "message": f"Successfully bought {order.quantity} shares of {order.symbol} at ${order.price:,.2f} each.",
            "total_cost": total_debit,
            "transaction_fee": transaction_fee,
            "trade_id": str(trade_record["_id"])
        }

    @staticmethod
    def _execute_sell(order: Order) -> dict:
        """Executes a sell order."""
        # Get the current portfolio
        portfolio = Portfolio.get_portfolio(order.user_id)
        holdings = portfolio.get("holdings", {})
        
        if order.symbol not in holdings or holdings[order.symbol] < order.quantity:
            current_shares = holdings.get(order.symbol, 0)
            raise InsufficientSharesError(
                f"Not enough shares to sell. "
                f"Trying to sell: {order.quantity}, Owned: {current_shares}"
            )

        # Calculate proceeds
        total_value = order.quantity * order.price
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
            "message": f"Successfully sold {order.quantity} shares of {order.symbol} at ${order.price:,.2f} each.",
            "total_credit": total_credit,
            "transaction_fee": transaction_fee,
            "trade_id": str(trade_record["_id"])
        }

    @staticmethod
    def get_trade_history(user_id, limit=50):
        """Get the trade history for a user."""
        trades = db.get_user_trades(user_id, limit)
        return trades
