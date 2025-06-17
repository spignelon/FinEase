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

# Option chain operations
def save_option_chain_data(data):
    """Save option chain data to the database."""
    if not data or "records" not in data:
        return False
    
    timestamp = datetime.now()
    records = data["records"]
    
    # Prepare bulk operations
    bulk_ops = []
    
    for option_data in records.get("data", []):
        # Process CE data if available
        if "CE" in option_data:
            ce_data = option_data["CE"]
            ce_data["optionType"] = "CE"
            ce_data["timestamp"] = timestamp
            ce_data["rawTimestamp"] = records.get("timestamp")
            ce_data["underlyingValue"] = records.get("underlyingValue")
            
            # Create unique ID based on identifiable fields
            ce_id = f"{ce_data['identifier']}_{timestamp.strftime('%Y%m%d%H%M%S')}"
            bulk_ops.append(
                UpdateOne(
                    {"_id": ce_id},
                    {"$set": ce_data},
                    upsert=True
                )
            )
        
        # Process PE data if available
        if "PE" in option_data:
            pe_data = option_data["PE"]
            pe_data["optionType"] = "PE"
            pe_data["timestamp"] = timestamp
            pe_data["rawTimestamp"] = records.get("timestamp")
            pe_data["underlyingValue"] = records.get("underlyingValue")
            
            # Create unique ID based on identifiable fields
            pe_id = f"{pe_data['identifier']}_{timestamp.strftime('%Y%m%d%H%M%S')}"
            bulk_ops.append(
                UpdateOne(
                    {"_id": pe_id},
                    {"$set": pe_data},
                    upsert=True
                )
            )
    
    # Execute bulk operation if there are operations to perform
    if bulk_ops:
        option_chain_collection.bulk_write(bulk_ops)
        return True
    return False

def get_latest_option_chain(symbol="NIFTY", expiry=None):
    """Get the latest option chain data."""
    query = {"underlying": symbol}
    
    if expiry:
        query["expiryDate"] = expiry
    
    # Get the most recent timestamp
    latest = option_chain_collection.find_one(
        query,
        sort=[("timestamp", pymongo.DESCENDING)]
    )
    
    if not latest:
        return []
    
    # Get all records from that timestamp
    latest_data = option_chain_collection.find(
        {"timestamp": latest["timestamp"], "underlying": symbol}
    )
    
    return list(latest_data)

# Trade operations
def record_trade(user_id, symbol, quantity, price, order_type, trade_time=None):
    """Record a trade in the database."""
    if not trade_time:
        trade_time = datetime.now()
        
    trade = {
        "user_id": user_id,
        "symbol": symbol,
        "quantity": quantity,
        "price": price,
        "order_type": order_type,
        "timestamp": trade_time,
        "total_value": quantity * price
    }
    
    trades_collection.insert_one(trade)
    return trade

def get_user_trades(user_id, limit=50):
    """Get trades for a specific user."""
    return list(
        trades_collection.find(
            {"user_id": user_id},
            sort=[("timestamp", pymongo.DESCENDING)],
            limit=limit
        )
    )

# Market data operations
def save_market_data(data):
    """Save market status data."""
    if not data:
        return False
    
    timestamp = datetime.now()
    data["timestamp"] = timestamp
    
    market_data_collection.insert_one(data)
    return True

def get_latest_market_data():
    """Get the latest market data."""
    return market_data_collection.find_one(
        sort=[("timestamp", pymongo.DESCENDING)]
    )

# Initialize database with indexes
setup_indexes()
setup_indexes()
