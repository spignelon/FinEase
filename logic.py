import dataclasses
from typing import Dict, Union, List, Optional
from datetime import datetime
import db

# --- Configuration ---
TRANSACTION_COST_FIXED = 40  # Fixed transaction fee of ₹40 per trade (replaces percentage-based fee)
SELL_MARGIN_PER_LOT = 200000  # 2 lakhs margin per lot for sell orders

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
            "short_positions": portfolio_data.get("short_positions", {}),
            "user_id": user_id
        }
    
    @staticmethod
    def update_holdings(user_id, symbol, quantity):
        """Updates the quantity of a stock in the portfolio."""
        db.update_portfolio_holdings(user_id, symbol, quantity)
    
    @staticmethod
    def update_short_positions(user_id, symbol, quantity, price):
        """Updates the short positions in the portfolio."""
        db.update_portfolio_short_positions(user_id, symbol, quantity, price)
    
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
        
        # Check if there's an existing short position that can be closed
        short_positions = portfolio.get("short_positions", {})
        if order.symbol in short_positions and short_positions[order.symbol]["quantity"] > 0:
            # This is a buy-to-cover order (closing a short position)
            return TradingSystem._execute_buy_to_cover(order, portfolio, short_positions)
        
        # Regular buy order logic (unchanged)
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
        transaction_fee = TRANSACTION_COST_FIXED  # Use fixed fee instead of percentage
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
    def _execute_buy_to_cover(order: Order, portfolio, short_positions) -> dict:
        """Executes a buy order that covers an existing short position."""
        symbol = order.symbol
        short_position = short_positions[symbol]
        short_quantity = short_position["quantity"]
        short_price = short_position["price"]
        
        # Limit the buy quantity to the short quantity
        cover_quantity = min(order.quantity, short_quantity)
        
        # Get lot size for the symbol
        lot_size = get_lot_size(symbol)
        
        # Get current price from LTP if available and price is 0
        if order.price == 0:
            try:
                option_data = db.get_option_with_ltp(symbol)
                if option_data and "lastPrice" in option_data and option_data["lastPrice"] is not None:
                    order.price = option_data["lastPrice"]
            except Exception as e:
                print(f"Error getting LTP for {symbol}: {e}")
        
        # Calculate costs
        units_per_lot = lot_size
        total_units = cover_quantity * units_per_lot
        unit_price = order.price
        total_cost = total_units * unit_price
        transaction_fee = TRANSACTION_COST_FIXED  # Use fixed fee
        total_debit = total_cost + transaction_fee
        
        # For short positions, profit is realized when the price goes down
        # Profit = (short price - cover price) * total_units - transaction fee
        # Fix: Only subtract transaction fee, not applying it twice
        realized_profit = (short_price - unit_price) * total_units - transaction_fee
        
        # Check if user has enough cash
        if total_debit > portfolio["cash"]:
            raise InsufficientFundsError(
                f"Not enough cash to cover {cover_quantity} lots of {symbol}. "
                f"Required: ₹{total_debit:,.2f}, Available: ₹{portfolio['cash']:,.2f}"
            )
        
        # Update portfolio
        Portfolio.update_cash(order.user_id, -total_debit)
        
        # Return margin if fully covering the position
        if cover_quantity == short_quantity:
            # Release the full margin amount
            margin_released = SELL_MARGIN_PER_LOT * short_quantity
            Portfolio.update_cash(order.user_id, margin_released)
        else:
            # Release margin proportionally
            margin_released = SELL_MARGIN_PER_LOT * cover_quantity
            Portfolio.update_cash(order.user_id, margin_released)
        
        # Update the short position
        Portfolio.update_short_positions(
            order.user_id, 
            symbol, 
            -cover_quantity,  # Reduce short position
            short_price  # Keep the same entry price
        )
        
        # Record the trade
        trade_record = db.record_trade(
            order.user_id,
            symbol,
            cover_quantity,  # Positive for buy
            order.price,
            "buy_to_cover",
            order.timestamp
        )
        
        return {
            "status": "success",
            "message": f"Successfully covered {cover_quantity} lots of {symbol} short position at ₹{order.price:,.2f} per unit. "
                     f"Margin released: ₹{margin_released:,.2f}, Realized P&L: ₹{realized_profit:,.2f}",
            "lot_size": lot_size,
            "total_units": total_units,
            "unit_price": unit_price,
            "total_cost": total_cost,
            "transaction_fee": transaction_fee,
            "total_debit": total_debit,
            "margin_released": margin_released,
            "realized_profit": realized_profit,
            "trade_id": str(trade_record["_id"])
        }

    @staticmethod
    def _execute_sell(order: Order) -> dict:
        """Executes a sell order."""
        # Get the current portfolio
        portfolio = Portfolio.get_portfolio(order.user_id)
        holdings = portfolio.get("holdings", {})
        
        # Check if selling from existing holdings or creating a new short position
        if order.symbol in holdings and holdings[order.symbol] > 0:
            # Selling from existing holdings (long position)
            return TradingSystem._execute_sell_long(order, portfolio, holdings)
        else:
            # Creating a new short position
            return TradingSystem._execute_short_sell(order, portfolio)
    
    @staticmethod
    def _execute_sell_long(order: Order, portfolio, holdings) -> dict:
        """Executes a sell order from existing holdings (long position)."""
        symbol = order.symbol
        available_quantity = holdings[symbol]
        
        if order.quantity > available_quantity:
            # If trying to sell more than owned, limit to available
            # and short sell the rest
            long_sell_quantity = available_quantity
            short_sell_quantity = order.quantity - available_quantity
            
            if short_sell_quantity > 0:
                # Create a modified order for the short sell portion
                short_order = Order(
                    symbol=symbol,
                    quantity=short_sell_quantity,
                    price=order.price,
                    order_type=order.order_type,
                    user_id=order.user_id,
                    timestamp=order.timestamp
                )
                
                # Execute long sell first
                long_result = TradingSystem._execute_sell_long_only(
                    Order(
                        symbol=symbol,
                        quantity=long_sell_quantity,
                        price=order.price,
                        order_type=order.order_type,
                        user_id=order.user_id,
                        timestamp=order.timestamp
                    ),
                    portfolio,
                    holdings
                )
                
                # Then execute short sell for remaining
                short_result = TradingSystem._execute_short_sell(short_order, portfolio)
                
                # Combine results
                return {
                    "status": "success",
                    "message": f"Sold {long_sell_quantity} owned lots and short sold {short_sell_quantity} lots of {symbol}.",
                    "long_sell": long_result,
                    "short_sell": short_result
                }
        
        # If selling less than or equal to what's owned, do a regular sell
        return TradingSystem._execute_sell_long_only(order, portfolio, holdings)
    
    @staticmethod
    def _execute_sell_long_only(order: Order, portfolio, holdings) -> dict:
        """Executes a sell order from existing holdings only."""
        symbol = order.symbol
        available_quantity = holdings[symbol]
        
        if order.quantity > available_quantity:
            raise InsufficientSharesError(
                f"Not enough lots to sell. "
                f"Trying to sell: {order.quantity} lots, Owned: {available_quantity} lots"
            )
        
        # Get lot size for the symbol
        lot_size = get_lot_size(symbol)
        
        # Get current price from LTP if available and price is 0
        if order.price == 0:
            try:
                option_data = db.get_option_with_ltp(symbol)
                if option_data and "lastPrice" in option_data and option_data["lastPrice"] is not None:
                    order.price = option_data["lastPrice"]
            except Exception as e:
                print(f"Error getting LTP for {symbol}: {e}")
        
        # Calculate proceeds
        units_per_lot = lot_size
        total_units = order.quantity * units_per_lot
        unit_price = order.price
        total_value = total_units * unit_price
        transaction_fee = TRANSACTION_COST_FIXED  # Use fixed fee
        total_credit = total_value - transaction_fee
        
        # Update portfolio
        Portfolio.update_cash(order.user_id, total_credit)
        Portfolio.update_holdings(order.user_id, symbol, -order.quantity)
        
        # Record the trade
        trade_record = db.record_trade(
            order.user_id,
            symbol,
            -order.quantity,  # Negative to indicate selling
            order.price,
            "sell",
            order.timestamp
        )
        
        return {
            "status": "success",
            "message": f"Successfully sold {order.quantity} lots ({total_units} units) of {symbol} at ₹{order.price:,.2f} per unit.",
            "lot_size": lot_size,
            "total_units": total_units,
            "unit_price": unit_price,
            "total_value": total_value,
            "transaction_fee": transaction_fee,
            "total_credit": total_credit,
            "trade_id": str(trade_record["_id"])
        }
    
    @staticmethod
    def _execute_short_sell(order: Order, portfolio) -> dict:
        """Executes a short sell order (selling without owning)."""
        symbol = order.symbol
        
        # Calculate required margin based on fixed amount per lot
        required_margin = SELL_MARGIN_PER_LOT * order.quantity
        
        # Check if user has enough cash to cover the margin
        if portfolio["cash"] < required_margin:
            raise InsufficientFundsError(
                f"Not enough cash for margin to short {order.quantity} lots of {symbol}. "
                f"Required margin: ₹{required_margin:,.2f}, Available: ₹{portfolio['cash']:,.2f}"
            )
        
        # Get lot size for the symbol
        lot_size = get_lot_size(symbol)
        
        # Get current price from LTP if available and price is 0
        if order.price == 0:
            try:
                option_data = db.get_option_with_ltp(symbol)
                if option_data and "lastPrice" in option_data and option_data["lastPrice"] is not None:
                    order.price = order.price or option_data["lastPrice"]
            except Exception as e:
                print(f"Error getting LTP for {symbol}: {e}")
        
        # Calculate values for record keeping
        units_per_lot = lot_size
        total_units = order.quantity * units_per_lot
        unit_price = order.price
        
        # Note: Transaction fee (TRANSACTION_COST_FIXED) will be applied when position is closed
        
        # Update portfolio - reserve margin and update short positions
        Portfolio.update_cash(order.user_id, -required_margin)  # Reserve margin
        Portfolio.update_short_positions(order.user_id, symbol, order.quantity, unit_price)
        
        # Record the trade
        trade_record = db.record_trade(
            order.user_id,
            symbol,
            -order.quantity,  # Negative to indicate selling/shorting
            order.price,
            "short_sell",
            order.timestamp
        )
        
        return {
            "status": "success",
            "message": f"Successfully short sold {order.quantity} lots ({total_units} units) of {symbol} at ₹{order.price:,.2f} per unit. "
                     f"Margin reserved: ₹{required_margin:,.2f}",
            "lot_size": lot_size,
            "total_units": total_units,
            "unit_price": unit_price,
            "margin_reserved": required_margin,
            "trade_id": str(trade_record["_id"])
        }

    @staticmethod
    def get_trade_history(user_id, limit=50):
        """Get the trade history for a user."""
        trades = db.get_user_trades(user_id, limit)
        return trades
