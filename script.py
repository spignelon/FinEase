# main.py
import dataclasses
from typing import Dict, Union

# --- Configuration ---
TRANSACTION_COST_PERCENT = 0.0075 # 0.75% transaction fee

# --- Custom Exceptions ---
class InsufficientFundsError(Exception):
    """Raised when trying to buy without enough cash."""
    pass

class InsufficientSharesError(Exception):
    """Raised when trying to sell more shares than owned."""
    pass

# --- Data Class for Orders ---
@dataclasses.dataclass
class Order:
    """Represents a buy or sell order."""
    ticker: str
    quantity: int
    price: float
    order_type: str # 'buy' or 'sell'

# --- Portfolio Management ---
class Portfolio:
    """Manages user's assets, including cash and stock holdings."""

    def __init__(self, initial_cash: float):
        self.cash: float = initial_cash
        self.holdings: Dict[str, int] = {} # {ticker: quantity}

    def update_holdings(self, ticker: str, quantity: int):
        """Updates the quantity of a stock in the portfolio."""
        self.holdings[ticker] = self.holdings.get(ticker, 0) + quantity
        if self.holdings[ticker] <= 0:
            del self.holdings[ticker] # Remove if no shares are left

    def view_portfolio(self):
        """Displays the current portfolio status."""
        print("\n--- Portfolio ---")
        print(f"Cash: ${self.cash:,.2f}")
        if not self.holdings:
            print("Holdings: No shares owned.")
        else:
            print("Holdings:")
            for ticker, quantity in self.holdings.items():
                print(f"  - {ticker}: {quantity} shares")
        print("------------------\n")

# --- Core Trading Logic ---
class TradingSystem:
    """Handles the execution of trades and interacts with the portfolio."""

    def __init__(self, portfolio: Portfolio):
        self.portfolio = portfolio

    def execute_trade(self, order: Order) -> str:
        """
        Executes a trade based on the provided order.
        Returns a confirmation message.
        """
        if order.order_type.lower() == 'buy':
            return self._execute_buy(order)
        elif order.order_type.lower() == 'sell':
            return self._execute_sell(order)
        else:
            return "Error: Invalid order type. Use 'buy' or 'sell'."

    def _execute_buy(self, order: Order) -> str:
        """Executes a buy order."""
        total_cost = order.quantity * order.price
        transaction_fee = total_cost * TRANSACTION_COST_PERCENT
        total_debit = total_cost + transaction_fee

        if total_debit > self.portfolio.cash:
            raise InsufficientFundsError(
                f"Not enough cash to buy {order.quantity} of {order.ticker}. "
                f"Required: ${total_debit:,.2f}, Available: ${self.portfolio.cash:,.2f}"
            )

        self.portfolio.cash -= total_debit
        self.portfolio.update_holdings(order.ticker, order.quantity)

        return (f"Successfully bought {order.quantity} shares of {order.ticker} "
                f"at ${order.price:,.2f} each. Total cost: ${total_debit:,.2f}")

    def _execute_sell(self, order: Order) -> str:
        """Executes a sell order."""
        if order.ticker not in self.portfolio.holdings or \
           order.quantity > self.portfolio.holdings[order.ticker]:
            current_shares = self.portfolio.holdings.get(order.ticker, 0)
            raise InsufficientSharesError(
                f"Not enough shares to sell. "
                f"Trying to sell: {order.quantity}, Owned: {current_shares}"
            )

        total_value = order.quantity * order.price
        transaction_fee = total_value * TRANSACTION_COST_PERCENT
        total_credit = total_value - transaction_fee

        self.portfolio.cash += total_credit
        self.portfolio.update_holdings(order.ticker, -order.quantity)

        return (f"Successfully sold {order.quantity} shares of {order.ticker} "
                f"at ${order.price:,.2f} each. Total credit: ${total_credit:,.2f}")

# --- Command-Line Interface ---
def main():
    """Main function to run the trading simulation."""
    try:
        initial_cash = float(input("Enter initial cash amount: $"))
    except ValueError:
        print("Invalid input. Starting with $10,000.")
        initial_cash = 10000.0

    portfolio = Portfolio(initial_cash=initial_cash)
    trading_system = TradingSystem(portfolio=portfolio)

    print("\nWelcome to the OOP Trading Simulator!")
    portfolio.view_portfolio()

    while True:
        action = input("Enter action (buy, sell, view, exit): ").lower()

        if action == 'exit':
            print("Exiting simulator. Final portfolio:")
            portfolio.view_portfolio()
            break
        elif action == 'view':
            portfolio.view_portfolio()
            continue
        elif action not in ['buy', 'sell']:
            print("Invalid action. Please choose 'buy', 'sell', 'view', or 'exit'.")
            continue

        try:
            ticker = input("Enter stock ticker (e.g., AAPL): ").upper()
            quantity = int(input("Enter quantity: "))
            price = float(input("Enter price per share: $"))

            if quantity <= 0 or price <= 0:
                print("Error: Quantity and price must be positive numbers.")
                continue

            order = Order(ticker=ticker, quantity=quantity, price=price, order_type=action)
            confirmation = trading_system.execute_trade(order)
            print(f"\n{confirmation}")
            portfolio.view_portfolio()

        except ValueError:
            print("\nError: Invalid input. Quantity must be an integer and price must be a number.")
        except (InsufficientFundsError, InsufficientSharesError) as e:
            print(f"\nError: {e}")
        except Exception as e:
            print(f"\nAn unexpected error occurred: {e}")


if __name__ == "__main__":
    main()

