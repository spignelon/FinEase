import pymongo
from pymongo import UpdateOne
from datetime import datetime
import json
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# MongoDB connection setup with URI from environment variables
mongodb_uri = os.environ.get('MONGODB_URI', 'mongodb://admin:password@localhost:27017/')

try:
    client = pymongo.MongoClient(mongodb_uri)
    # Test the connection
    client.admin.command('ping')
    print("MongoDB connection successful")
except pymongo.errors.ConnectionFailure as e:
    print(f"MongoDB connection failed: {e}")
    # Using a fallback in-memory structure for development
    print("Warning: Using in-memory fallback - data will not persist!")
    client = None

# Database setup
db = client["paper_trading"] if client is not None else None

# Collections
users_collection = db["users"] if db is not None else None
portfolios_collection = db["portfolios"] if db is not None else None
option_chain_collection = db["option_chain"] if db is not None else None
trades_collection = db["trades"] if db is not None else None
market_data_collection = db["market_data"] if db is not None else None
master_collection = db["master"] if db is not None else None  # Added master collection
ltp_collection = db["ltp"] if db is not None else None  # Added ltp collection

# Initialize indexes
def setup_indexes():
    """Set up necessary indexes for performance."""
    if client is None:
        print("Skipping index creation - no MongoDB connection")
        return
        
    try:
        option_chain_collection.create_index([("timestamp", pymongo.DESCENDING)])
        option_chain_collection.create_index([("symbol", pymongo.ASCENDING)])
        option_chain_collection.create_index([("expiryDate", pymongo.ASCENDING)])
        option_chain_collection.create_index([("strikePrice", pymongo.ASCENDING)])
        option_chain_collection.create_index([("optionType", pymongo.ASCENDING)])
        
        trades_collection.create_index([("user_id", pymongo.ASCENDING)])
        trades_collection.create_index([("timestamp", pymongo.DESCENDING)])
        
        portfolios_collection.create_index([("user_id", pymongo.ASCENDING)], unique=True)
        
        # Add index for the master collection
        master_collection.create_index([("fetched_date", pymongo.DESCENDING)])
        master_collection.create_index([("symbol", pymongo.ASCENDING)])
        master_collection.create_index([("token", pymongo.ASCENDING)])
        
        # Add index for the ltp collection
        ltp_collection.create_index([("token", pymongo.ASCENDING)])
        ltp_collection.create_index([("created_at", pymongo.DESCENDING)])
        
        print("MongoDB indexes created successfully")
    except Exception as e:
        print(f"Error creating indexes: {e}")

# User operations
def create_user(username, password_hash, email):
    """Create a new user."""
    user = {
        "username": username,
        "password_hash": password_hash,
        "email": email,
        "created_at": datetime.now()
    }
    users_collection.insert_one(user)
    
    # Create an empty portfolio for the user
    create_portfolio(user["_id"], 1000000)  # Default 10 lakh initial cash
    return user

def get_user_by_username(username):
    """Get user by username."""
    return users_collection.find_one({"username": username})

# Portfolio operations
def create_portfolio(user_id, initial_cash=1000000):
    """Create a new portfolio for a user."""
    portfolio = {
        "user_id": user_id,
        "cash": initial_cash,
        "holdings": {},
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }
    portfolios_collection.insert_one(portfolio)
    return portfolio

def get_portfolio(user_id):
    """Get portfolio for a user."""
    return portfolios_collection.find_one({"user_id": user_id})

def update_portfolio_cash(user_id, cash_change):
    """Update user's cash balance."""
    portfolios_collection.update_one(
        {"user_id": user_id},
        {
            "$inc": {"cash": cash_change},
            "$set": {"updated_at": datetime.now()}
        }
    )

def update_portfolio_holdings(user_id, symbol, quantity_change):
    """Update user's holdings for a specific symbol."""
    portfolio = portfolios_collection.find_one({"user_id": user_id})
    
    # Get current holdings
    holdings = portfolio.get("holdings", {})
    current_quantity = holdings.get(symbol, 0)
    new_quantity = current_quantity + quantity_change
    
    # Update holdings
    if new_quantity <= 0:
        # Remove the holding if no shares left
        holdings.pop(symbol, None)
    else:
        holdings[symbol] = new_quantity
    
    # Update in database
    portfolios_collection.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "holdings": holdings,
                "updated_at": datetime.now()
            }
        }
    )

# Trade operations
def record_trade(user_id, symbol, quantity, price, order_type, trade_time=None):
    """Record a trade in the database."""
    if client is None:
        return {"_id": "mock_id", "status": "in-memory-fallback"}
        
    if not trade_time:
        trade_time = datetime.now()
        
    trade = {
        "user_id": user_id,
        "symbol": symbol,
        "quantity": quantity,
        "price": price,
        "order_type": order_type,
        "timestamp": trade_time,
        "total_value": abs(quantity) * price
    }
    
    result = trades_collection.insert_one(trade)
    trade["_id"] = result.inserted_id
    return trade

def get_user_trades(user_id, limit=50):
    """Get trades for a specific user."""
    if client is None:
        return []
        
    return list(
        trades_collection.find(
            {"user_id": user_id},
            sort=[("timestamp", pymongo.DESCENDING)],
            limit=limit
        )
    )

# Option parsing and fetching functions
def parse_option_symbol(symbol):
    """
    Parse an option symbol (e.g., NIFTY26JUN2523050PE) to extract its components.
    
    Args:
        symbol (str): The option symbol to parse
        
    Returns:
        dict: A dictionary containing the parsed components
    """
    if not symbol or len(symbol) < 10:
        return None
    
    try:
        # Extract the underlying (first 5 characters for NIFTY)
        underlying = symbol[:5]
        
        # The last 2 characters are always the option type (CE or PE)
        option_type = symbol[-2:]
        
        # For extracting expiry and strike, we need to separate them
        middle_part = symbol[5:-2]  # This contains both expiry and strike
        
        # The first 7 characters of the middle part are the expiry (26JUN25)
        expiry = middle_part[:7]
        
        # The rest is the strike price
        strike_price = int(middle_part[7:])
        
        return {
            "underlying": underlying,
            "expiry": expiry,
            "strike_price": strike_price,
            "option_type": option_type,
            "symbol": symbol
        }
    except Exception as e:
        print(f"Error parsing option symbol {symbol}: {e}")
        return None

def get_options_from_master(underlying="NIFTY", expiry=None):
    """
    Get option data from the master collection based on underlying and optionally expiry.
    
    Args:
        underlying (str): The underlying asset (default: NIFTY)
        expiry (str, optional): The expiry date in format like 26JUN25
        
    Returns:
        list: List of option data from the master collection
    """
    if client is None:
        return []
    
    query = {"name": underlying}
    
    if expiry:
        query["expiry"] = expiry
    
    # Get the latest fetched date
    latest_record = master_collection.find_one(
        sort=[("fetched_date", pymongo.DESCENDING)]
    )
    
    if latest_record:
        # Only get records from the latest fetched batch
        query["fetched_date"] = latest_record["fetched_date"]
    
    options_data = list(master_collection.find(query))
    
    # Parse and enrich each option with strike price and option type
    enriched_options = []
    for option in options_data:
        parsed = parse_option_symbol(option["symbol"])
        if parsed:
            # Add the parsed data to the option document
            option.update({
                "strikePrice": parsed["strike_price"],
                "optionType": parsed["option_type"],
                "underlying": underlying,
                "expiryDate": parsed["expiry"]
            })
            enriched_options.append(option)
    
    return enriched_options

def get_latest_ltp(token):
    """
    Get the latest LTP (Last Traded Price) for a given token.
    
    Args:
        token (str): The token to look up
        
    Returns:
        float: The latest LTP value, or None if not found
    """
    if client is None:
        return None
    
    latest_ltp = ltp_collection.find_one(
        {"token": token},
        sort=[("created_at", pymongo.DESCENDING)]
    )
    
    if latest_ltp and "last_traded_price" in latest_ltp:
        # The LTP value needs to be divided by 100 to get the actual price
        return latest_ltp["last_traded_price"] / 100.0
    
    return None

def get_option_with_ltp(symbol):
    """
    Get option data with the latest LTP for a given symbol.
    
    Args:
        symbol (str): The option symbol
        
    Returns:
        dict: Option data with LTP, or None if not found
    """
    if client is None:
        return None
    
    # Get option data from master collection
    option = master_collection.find_one({"symbol": symbol})
    
    if not option:
        return None
    
    # Get LTP data
    token = option.get("token")
    ltp = get_latest_ltp(token) if token else None
    
    # Parse symbol to get strike price and option type
    parsed = parse_option_symbol(symbol)
    if parsed:
        option.update({
            "strikePrice": parsed["strike_price"],
            "optionType": parsed["option_type"],
            "underlying": parsed["underlying"],
            "expiryDate": parsed["expiry"],
            "lastPrice": ltp
        })
    
    return option

def get_latest_option_chain(symbol="NIFTY", expiry=None):
    """
    Get option chain data from master collection with LTP data.
    This replaces the previous function that fetched from NSE API.
    
    Args:
        symbol (str): The underlying symbol (default: NIFTY)
        expiry (str, optional): The expiry date
        
    Returns:
        list: List of options with LTP data
    """
    options = get_options_from_master(symbol, expiry)
    
    # Add LTP data to each option
    for option in options:
        token = option.get("token")
        if token:
            ltp = get_latest_ltp(token)
            option["lastPrice"] = ltp
    
    return options

# Master data operations
def is_master_data_current():
    """
    Check if the master data in the database is from today.
    
    Returns:
        bool: True if master data is from today, False otherwise
    """
    if client is None:
        return False
        
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Find any record from today
    latest_record = master_collection.find_one(
        {"fetched_date": {"$gte": today}},
        sort=[("fetched_date", pymongo.DESCENDING)]
    )
    
    return latest_record is not None

def clear_master_collection():
    """
    Clear all data from the master collection.
    
    Returns:
        bool: True if successful, False if failed
    """
    if client is None:
        return False
    
    try:
        master_collection.delete_many({})
        return True
    except Exception as e:
        print(f"Error clearing master collection: {e}")
        return False

def save_master_data(master_data):
    """
    Save the fetched master data to the database.
    
    Args:
        master_data (list): List of dictionaries containing master data
    
    Returns:
        bool: True if successful, False if failed
    """
    if client is None or not master_data:
        return False
    
    try:
        # Add timestamp to each record
        fetched_date = datetime.now()
        for item in master_data:
            item["fetched_date"] = fetched_date
            
        # Insert all records
        master_collection.insert_many(master_data)
        return True
    except Exception as e:
        print(f"Error saving master data: {e}")
        return False

def get_master_data(symbol=None):
    """
    Get master data from the database, optionally filtered by symbol.
    
    Args:
        symbol (str, optional): Filter by symbol name
    
    Returns:
        list: List of master data records
    """
    if client is None:
        return []
    
    query = {}
    if symbol:
        query["symbol"] = symbol
    
    return list(master_collection.find(query, {'_id': 0}))

def get_latest_market_data():
    """
    Get the latest market data from the market_data_collection.
    
    Returns:
        dict: The latest market data document or a default market data structure if none found
    """
    if client is None:
        return default_market_data()
    
    latest = market_data_collection.find_one(
        sort=[("timestamp", pymongo.DESCENDING)]
    )
    
    if latest:
        return latest
    else:
        return default_market_data()

def default_market_data():
    """
    Provides default market data when no real data is available.
    
    Returns:
        dict: A dictionary containing default market data
    """
    current_time = datetime.now()
    
    return {
        "_id": "default",
        "timestamp": current_time,
        "marketState": [
            {
                "index": "NIFTY 50",
                "last": 22500,
                "change": 0,
                "pChange": 0
            },
            {
                "index": "BANKNIFTY",
                "last": 48000,
                "change": 0,
                "pChange": 0
            }
        ]
    }

def save_market_data(data):
    """Save market status data."""
    if not data or client is None:
        return False
    
    try:
        # Ensure timestamp is set
        if 'timestamp' not in data:
            data['timestamp'] = datetime.now()
            
        # Insert the market data
        market_data_collection.insert_one(data)
        print(f"Market data saved at {datetime.now()}")
        return True
    except Exception as e:
        print(f"Error saving market data: {e}")
        return False

# Initialize database with indexes
setup_indexes()
