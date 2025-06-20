import os
import json
import requests
import threading
import time
from flask import Flask, request, jsonify, abort
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import pymongo
from pymongo.errors import DuplicateKeyError
from functools import wraps
from bson.objectid import ObjectId
from bson.errors import InvalidId

import db
import logic
from master import NiftyDataProcessor  # Import NiftyDataProcessor from master.py

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_key_for_development')

# Configure CORS
CORS(app, resources={
    r"/api/*": {
        "origins": "*",  # For development; restrict this in production
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Authorization", "Content-Type"]
    }
})

# Global variables
running = True
session = requests.Session()  # Create a session to reuse connections

# Add required headers to mimic browser requests
headers = {
    'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
    'accept': '*/*',
    'accept-language': 'en-US,en;q=0.8',
    'referer': 'https://www.nseindia.com/option-chain',
    'sec-ch-ua': '"Brave";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Linux"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'sec-gpc': '1',
    'priority': 'u=1, i'
}

# Add cookies required for NSE API access
cookies = {
    'nsit': 'iI7Ov2YXr9cyM6LVAqyDD9JV',
    'nseappid': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJhcGkubnNlIiwiYXVkIjoiYXBpLm5zZSIsImlhdCI6MTc1MDE0NTA3NywiZXhwIjoxNzUwMTUyMjc3fQ.Q59zBon4yo0SXKX5-i9vIH-sMLU4t4Q564STtiI-asY',
    'AKA_A2': 'A',
}

# Update the session with the cookies
for cookie_name, cookie_value in cookies.items():
    session.cookies.set(cookie_name, cookie_value)

# Helper function to fetch data from the NSE API
def fetch_data(url):
    try:
        response = session.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error fetching data: Status code {response.status_code}")
            return None
    except Exception as e:
        print(f"Exception while fetching data: {str(e)}")
        return None

# Function to fetch option chain data periodically
def fetch_option_chain_data():
    global running
    while running:
        try:
            option_chain_url = "https://www.nseindia.com/api/option-chain-v3?type=Indices&symbol=NIFTY&expiry=19-Jun-2025"
            data = fetch_data(option_chain_url)
            if data:
                db.save_option_chain_data(data)
                print(f"Option chain data updated at {datetime.now()}")
            
            # Fetch market status data
            market_status_url = "https://www.nseindia.com/api/marketStatus"
            market_data = fetch_data(market_status_url)
            if market_data:
                db.save_market_data(market_data)
                print(f"Market data updated at {datetime.now()}")
                
        except Exception as e:
            print(f"Error in fetch_option_chain_data: {str(e)}")
        
        # Sleep for 2 seconds
        time.sleep(2)

# Authentication decorator
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            return jsonify({'message': 'Authorization header is missing!'}), 401
        
        # Check if token has Bearer prefix and remove it
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]  # Remove 'Bearer ' prefix
        else:
            token = auth_header
            
        print(f"Processing authentication with token: {token}")
        
        try:
            # Validate token format as MongoDB ObjectId
            if not ObjectId.is_valid(token):
                print(f"Invalid ObjectId format: {token}")
                return jsonify({'message': 'Invalid token format!'}), 401
                
            user_id = ObjectId(token)
            
            # Check if user exists
            user = db.users_collection.find_one({"_id": user_id})
            if not user:
                print(f"User not found for token: {token}")
                return jsonify({'message': 'User not found!'}), 401
            
            # Log successful authentication
            print(f"Authentication successful for user: {user['username']}")
            return f(str(user_id), *args, **kwargs)
            
        except InvalidId as e:
            print(f"Invalid ObjectId format error: {e}")
            return jsonify({'message': 'Invalid token format!'}), 401
        except Exception as e:
            print(f"Authentication error: {str(e)}")
            return jsonify({'message': f'Authentication error: {str(e)}'}), 401
        
    return decorated

# Function to fetch and update master data
def update_master_data():
    """
    Check if master data needs updating and fetch new data if required.
    
    Returns:
        bool: True if update was performed, False if not needed
    """
    print("Checking if master data needs to be updated...")
    
    # Check if the master data is already current (from today)
    if db.is_master_data_current():
        print("Master data is already current. Skipping update.")
        return False
    
    print("Master data is outdated or missing. Fetching new data...")
    
    # Clear existing master data
    db.clear_master_collection()
    
    # Use NiftyDataProcessor to fetch new master data
    data_url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
    processor = NiftyDataProcessor(data_url)
    
    if processor.fetch_data():
        filtered_results = processor.get_filtered_nifty_data()
        
        if filtered_results:
            # Save the filtered results to the master collection
            success = db.save_master_data(filtered_results)
            if success:
                print(f"Master data updated successfully with {len(filtered_results)} records")
            else:
                print("Failed to save master data to database")
            return success
        else:
            print("No filtered results found in master data")
            return False
    else:
        print("Failed to fetch master data")
        return False

# Routes
@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    
    required_fields = ['username', 'password', 'email']
    for field in required_fields:
        if field not in data:
            return jsonify({'message': f'Missing required field: {field}'}), 400
    
    username = data['username']
    password = data['password']
    email = data['email']
    
    # Check if username already exists
    if db.get_user_by_username(username):
        return jsonify({'message': 'Username already exists'}), 400
    
    # Hash the password
    password_hash = generate_password_hash(password)
    
    try:
        # Create user
        user = db.create_user(username, password_hash, email)
        
        # Return success with user_id as the token (simplified)
        return jsonify({
            'message': 'User registered successfully',
            'token': str(user['_id']),
            'user_id': str(user['_id']),
            'username': username
        }), 201
        
    except DuplicateKeyError:
        return jsonify({'message': 'Username already exists'}), 400
    except Exception as e:
        return jsonify({'message': f'Registration failed: {str(e)}'}), 500

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({'message': 'Missing username or password'}), 400
    
    username = data['username']
    password = data['password']
    
    user = db.get_user_by_username(username)
    
    if not user or not check_password_hash(user['password_hash'], password):
        return jsonify({'message': 'Invalid username or password'}), 401
    
    # Return token (in a real app, you'd generate a proper JWT or OAuth token)
    return jsonify({
        'message': 'Login successful',
        'token': str(user['_id']),
        'user_id': str(user['_id']),
        'username': username
    }), 200

@app.route('/api/portfolio', methods=['GET'])
@token_required
def get_portfolio(user_id):
    portfolio = logic.Portfolio.get_portfolio(user_id)
    
    # Get latest market data for valuation
    market_data = db.get_latest_market_data()
    nifty_price = 0
    if market_data and 'marketState' in market_data:
        for state in market_data['marketState']:
            if state.get('index') == 'NIFTY 50':
                nifty_price = state.get('last', 0)
    
    # Calculate total value (simplified - in a real app, you'd use actual prices)
    holdings_list = []
    total_holdings_value = 0
    
    for symbol, quantity in portfolio['holdings'].items():
        try:
            # Try to get current price for the holding
            option_data = logic.OptionChain.get_option_by_symbol(symbol)
            price = option_data.get('lastPrice', 0)
            lot_size = logic.get_lot_size(symbol)
            total_units = quantity * lot_size
            market_value = total_units * price
            total_holdings_value += market_value
            
            holdings_list.append({
                'symbol': symbol,
                'quantity': quantity,
                'lot_size': lot_size,
                'total_units': total_units,
                'price': price,
                'market_value': market_value
            })
        except Exception as e:
            # If there's an error getting the price, use a placeholder
            holdings_list.append({
                'symbol': symbol,
                'quantity': quantity,
                'lot_size': logic.get_lot_size(symbol),
                'price': 'Unknown',
                'market_value': 0,
                'error': str(e)
            })
    
    return jsonify({
        'cash': portfolio['cash'],
        'holdings': holdings_list,
        'total_holdings_value': total_holdings_value,
        'total_portfolio_value': portfolio['cash'] + total_holdings_value,
        'nifty_price': nifty_price
    }), 200

@app.route('/api/option_chain', methods=['GET'])
def get_option_chain():
    symbol = request.args.get('symbol', 'NIFTY')
    expiry = request.args.get('expiry')
    
    options_data = db.get_latest_option_chain(symbol, expiry)
    
    # Format the data for the frontend
    formatted_options = []
    for option in options_data:
        formatted_symbol = logic.OptionChain.format_symbol(
            option["underlying"],
            option["expiryDate"],
            option["strikePrice"],
            option["optionType"]
        )
        
        option["formattedSymbol"] = formatted_symbol
        formatted_options.append(option)
    
    return jsonify({
        'options': formatted_options,
        'timestamp': datetime.now().isoformat(),
        'count': len(formatted_options)
    }), 200

@app.route('/api/options/search', methods=['GET'])
def search_options():
    query = request.args.get('q', '')
    
    if not query or len(query) < 2:
        return jsonify({
            'options': [],
            'message': 'Query too short'
        }), 400
    
    results = logic.OptionChain.search_options(query)
    
    return jsonify({
        'options': results,
        'count': len(results)
    }), 200

@app.route('/api/trade', methods=['POST'])
@token_required
def execute_trade(user_id):
    data = request.json
    
    required_fields = ['symbol', 'quantity', 'price', 'order_type']
    for field in required_fields:
        if field not in data:
            return jsonify({'message': f'Missing required field: {field}'}), 400
    
    try:
        # Create order
        order = logic.Order(
            symbol=data['symbol'],
            quantity=int(data['quantity']),
            price=float(data['price']),
            order_type=data['order_type'],
            user_id=user_id,
            timestamp=datetime.now()
        )
        
        # Execute trade
        result = logic.TradingSystem.execute_trade(order)
        
        return jsonify(result), 200
        
    except logic.InsufficientFundsError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400
    except logic.InsufficientSharesError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400
    except logic.InvalidSymbolError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400
    except ValueError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'An unexpected error occurred: {str(e)}'}), 500

@app.route('/api/trades', methods=['GET'])
@token_required
def get_trades(user_id):
    limit = request.args.get('limit', 50, type=int)
    
    trades = logic.TradingSystem.get_trade_history(user_id, limit)
    
    # Convert ObjectId to string for JSON serialization
    for trade in trades:
        trade['_id'] = str(trade['_id'])
        trade['user_id'] = str(trade['user_id'])
        # Format the timestamp
        trade['timestamp'] = trade['timestamp'].isoformat()
    
    return jsonify({
        'trades': trades,
        'count': len(trades)
    }), 200

@app.route('/api/market_data', methods=['GET'])
def get_market_data():
    market_data = db.get_latest_market_data()
    
    if not market_data:
        return jsonify({
            'status': 'error',
            'message': 'No market data available'
        }), 404
    
    # Convert ObjectId to string for JSON serialization
    market_data['_id'] = str(market_data['_id'])
    
    return jsonify(market_data), 200

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'message': 'Resource not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'message': 'Internal server error'}), 500

# Replace the deprecated before_first_request with proper initialization
def start_background_tasks():
    # First, update master data if needed
    update_master_data()
    
    # Then start the regular data fetching thread
    data_thread = threading.Thread(target=fetch_option_chain_data)
    data_thread.daemon = True
    data_thread.start()
    return data_thread

# Add a new API endpoint to manually trigger master data update (useful for testing)
@app.route('/api/admin/update_master_data', methods=['POST'])
@token_required
def admin_update_master_data(user_id):
    # In a real app, you'd check if the user has admin privileges
    result = update_master_data()
    return jsonify({
        'success': result,
        'message': 'Master data updated successfully' if result else 'No update needed or update failed'
    })

if __name__ == '__main__':
    try:
        # Create a thread for fetching data
        data_thread = start_background_tasks()
        
        # Run the Flask app
        app.run(debug=True, host='0.0.0.0', port=5000)
    finally:
        # Set the flag to stop the thread
        running = False
        print("Shutting down background tasks...")
