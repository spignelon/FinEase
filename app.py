import os
import json
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
import fetch_nifty  # Import the new fetch_nifty module
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
    
    # Calculate total value of long positions (holdings)
    holdings_list = []
    total_holdings_value = 0
    
    for symbol, quantity in portfolio['holdings'].items():
        try:
            # Get option data with LTP from MongoDB
            option_data = db.get_option_with_ltp(symbol)
            
            if option_data and "lastPrice" in option_data and option_data["lastPrice"] is not None:
                price = option_data["lastPrice"]
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
                    'market_value': market_value,
                    'position_type': 'long'
                })
            else:
                # If no LTP available
                holdings_list.append({
                    'symbol': symbol,
                    'quantity': quantity,
                    'lot_size': logic.get_lot_size(symbol),
                    'price': 'Unknown',
                    'market_value': 0,
                    'position_type': 'long',
                    'error': 'No LTP data available'
                })
        except Exception as e:
            # If there's an error getting the price, use a placeholder
            holdings_list.append({
                'symbol': symbol,
                'quantity': quantity,
                'lot_size': logic.get_lot_size(symbol),
                'price': 'Unknown',
                'market_value': 0,
                'position_type': 'long',
                'error': str(e)
            })
    
    # Calculate value and PnL for short positions
    short_positions = portfolio.get('short_positions', {})
    short_positions_list = []
    total_short_value = 0
    total_short_pnl = 0
    total_margin_frozen = 0
    
    for symbol, position in short_positions.items():
        try:
            entry_price = position.get('price', 0)
            quantity = position.get('quantity', 0)
            
            # Get current price
            option_data = db.get_option_with_ltp(symbol)
            
            if option_data and "lastPrice" in option_data and option_data["lastPrice"] is not None:
                current_price = option_data["lastPrice"]
                lot_size = logic.get_lot_size(symbol)
                total_units = quantity * lot_size
                
                # Calculate frozen margin (2 lakhs per lot)
                margin_frozen = logic.SELL_MARGIN_PER_LOT * quantity
                total_margin_frozen += margin_frozen
                
                # For short positions, PnL = (entry_price - current_price) * total_units
                # If entry_price > current_price, it's a profit; if entry_price < current_price, it's a loss
                pnl = (entry_price - current_price) * total_units
                total_short_pnl += pnl
                
                # Market value is the value at the current price
                market_value = total_units * current_price
                total_short_value += market_value
                
                short_positions_list.append({
                    'symbol': symbol,
                    'quantity': -quantity,  # Display as negative to indicate short position
                    'lot_size': lot_size,
                    'total_units': -total_units,  # Also make total units negative
                    'entry_price': entry_price,
                    'price': entry_price,  # Add price field with entry price
                    'current_price': current_price,
                    'pnl': pnl,
                    'margin_frozen': margin_frozen,
                    'market_value': market_value,
                    'position_type': 'short'
                })
            else:
                # If no LTP available
                margin_frozen = logic.SELL_MARGIN_PER_LOT * quantity
                total_margin_frozen += margin_frozen
                
                short_positions_list.append({
                    'symbol': symbol,
                    'quantity': -quantity,  # Display as negative to indicate short position
                    'lot_size': logic.get_lot_size(symbol),
                    'entry_price': entry_price,
                    'price': entry_price,  # Add price field with entry price
                    'current_price': 'Unknown',
                    'pnl': 0,
                    'margin_frozen': margin_frozen,
                    'market_value': 0,
                    'position_type': 'short',
                    'error': 'No LTP data available'
                })
        except Exception as e:
            margin_frozen = logic.SELL_MARGIN_PER_LOT * quantity
            total_margin_frozen += margin_frozen
            
            short_positions_list.append({
                'symbol': symbol,
                'quantity': -quantity,  # Display as negative to indicate short position
                'lot_size': logic.get_lot_size(symbol),
                'entry_price': entry_price,
                'price': entry_price,  # Add price field with entry price
                'current_price': 'Unknown',
                'pnl': 0,
                'margin_frozen': margin_frozen,
                'market_value': 0,
                'position_type': 'short',
                'error': str(e)
            })
    
    # Combine all positions for display
    all_positions = holdings_list + short_positions_list
    
    # Calculate the adjusted cash and portfolio value correctly
    # When a short position is created, cash decreases by the margin amount
    # The correct way to calculate total portfolio value is to add the margin back
    # since it's not actually "spent" - just frozen as collateral
    
    adjusted_portfolio_value = portfolio['cash'] + total_holdings_value + total_short_pnl + total_margin_frozen
    
    return jsonify({
        'cash': portfolio['cash'],
        'available_cash': portfolio['cash'] - total_margin_frozen,
        'margin_frozen': total_margin_frozen,
        'holdings': all_positions,
        'long_holdings_value': total_holdings_value,
        'short_positions_value': total_short_value,
        'short_positions_pnl': total_short_pnl,
        'total_holdings_value': total_holdings_value + total_short_pnl,
        # Add margin frozen to portfolio value to offset the reduction in cash
        'total_portfolio_value': adjusted_portfolio_value,
        'nifty_price': nifty_price,
        # Add this field to make it easier for the frontend to understand
        'effective_portfolio_value': portfolio['cash'] + total_holdings_value + total_short_pnl,
        # Include initial portfolio value for reference
        'initial_portfolio_value': 1000000  # 10 lakhs starting cash
    }), 200

@app.route('/api/option_chain', methods=['GET'])
def get_option_chain():
    symbol = request.args.get('symbol', 'NIFTY')
    expiry = request.args.get('expiry')
    
    # Get option chain data from MongoDB with LTP
    options_data = db.get_latest_option_chain(symbol, expiry)
    
    # Format the data for the frontend
    formatted_options = []
    for option in options_data:
        formatted_symbol = option.get("symbol", "")
        
        option_dict = {
            "formattedSymbol": formatted_symbol,
            "symbol": formatted_symbol,
            "underlying": option.get("underlying", symbol),
            "expiryDate": option.get("expiryDate", ""),
            "strikePrice": option.get("strikePrice", 0),
            "optionType": option.get("optionType", ""),
            "lastPrice": option.get("lastPrice", None),
            "token": option.get("token", "")
        }
        
        formatted_options.append(option_dict)
    
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
    
    # Get master data first
    all_options = db.get_options_from_master()
    
    # Filter based on query
    query = query.upper()
    results = []
    
    for option in all_options:
        if query in option.get("symbol", ""):
            # Add LTP data
            token = option.get("token")
            if token:
                ltp = db.get_latest_ltp(token)
                option["lastPrice"] = ltp
                
            # Create a clean response object
            results.append({
                "formattedSymbol": option.get("symbol", ""),
                "symbol": option.get("symbol", ""),
                "underlying": option.get("underlying", "NIFTY"),
                "expiryDate": option.get("expiryDate", ""),
                "strikePrice": option.get("strikePrice", 0),
                "optionType": option.get("optionType", ""),
                "lastPrice": option.get("lastPrice"),
                "token": option.get("token", "")
            })
            
            # Limit to 20 results
            if len(results) >= 20:
                break
    
    # Fix: Return jsonify result and status code separately
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
    # Try to fetch fresh market data
    fresh_data = fetch_nifty.update_market_data()
    
    # If fresh fetch fails, get the latest data from database
    market_data = fresh_data or db.get_latest_market_data()
    
    if not market_data:
        return jsonify({
            'status': 'error',
            'message': 'No market data available'
        }), 404
    
    # Convert ObjectId to string for JSON serialization
    if '_id' in market_data:
        market_data['_id'] = str(market_data['_id'])
    
    return jsonify(market_data), 200

# New endpoint for fetching live NIFTY price
@app.route('/api/nifty_price', methods=['GET'])
def get_nifty_price():
    # NIFTY 50 token is 26000
    nifty_token = "26000"
    
    try:
        # Get the latest LTP for NIFTY
        nifty_price = db.get_latest_ltp(nifty_token)
        
        if nifty_price is not None:
            return jsonify({
                'status': 'success',
                'symbol': 'NIFTY 50',
                'price': nifty_price,
                'timestamp': datetime.now().isoformat()
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': 'NIFTY price data not available',
                'timestamp': datetime.now().isoformat()
            }), 404
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Error fetching NIFTY price: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }), 500

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'message': 'Resource not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'message': 'Internal server error'}), 500

# Replace NSE data fetching with master data update at startup
def start_background_tasks():
    # Update master data if needed
    update_master_data()
    
    # Start a thread to periodically fetch market data
    market_data_thread = threading.Thread(target=fetch_market_data_periodically)
    market_data_thread.daemon = True
    market_data_thread.start()
    
    return market_data_thread

def fetch_market_data_periodically():
    """Function to periodically fetch market data in a separate thread."""
    global running
    
    print("Starting market data fetching thread")
    # Fetch market data immediately at startup
    fetch_nifty.update_market_data()
    
    # Then fetch at regular intervals
    while running:
        try:
            time.sleep(60)  # Update every 60 seconds
            if running:  # Check if we should still be running
                fetch_nifty.update_market_data()
        except Exception as e:
            print(f"Error in market data thread: {e}")
            # Sleep for a bit before retrying
            time.sleep(10)

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
        # Start background tasks
        market_thread = start_background_tasks()
        
        # Run the Flask app
        app.run(debug=True, host='0.0.0.0', port=5001)
    finally:
        # Signal to stop any background tasks
        running = False
        print("Shutting down background tasks...")
        time.sleep(1)  # Give threads a chance to terminate gracefully
