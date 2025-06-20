import threading
import time
import pyotp
from SmartApi import SmartConnect
from SmartApi.smartWebSocketV2 import SmartWebSocketV2
from pymongo import MongoClient, ASCENDING
from pymongo.errors import ConnectionFailure
from config import *

# --- MongoDB Configuration ---
MONGO_URI = "mongodb://admin:password118@localhost:27017/"
DB_NAME = "paper_trading"
MASTER_COLLECTION = "master"
LTP_COLLECTION = "ltp"

# --- Global Variables ---
ltp_collection = None

def get_tokens_from_mongodb():
    """
    Fetches the list of tokens from the 'master' collection in MongoDB.
    """
    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        master_collection = db[MASTER_COLLECTION]
        tokens = [doc['token'] for doc in master_collection.find({}, {'token': 1, '_id': 0})]
        client.close()
        print(f"Successfully fetched {len(tokens)} tokens from the 'master' collection.")
        return tokens
    except ConnectionFailure as e:
        print(f"Error connecting to MongoDB: {e}")
        return []
    except Exception as e:
        print(f"An error occurred while fetching tokens from MongoDB: {e}")
        return []

def setup_mongodb_connection():
    """
    Sets up the MongoDB connection and returns the ltp collection object.
    Also creates an index on 'token' for faster queries.
    """
    global ltp_collection
    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        ltp_collection = db[LTP_COLLECTION]
        # Create an index on the 'token' field to improve query performance
        ltp_collection.create_index([("token", ASCENDING)])
        print("Successfully connected to the 'ltp' collection in MongoDB.")
    except ConnectionFailure as e:
        print(f"Could not connect to MongoDB: {e}")
        exit()
    except Exception as e:
        print(f"An error occurred during MongoDB setup: {e}")
        exit()

def on_data(wsapp, message):
    """
    Callback function to handle incoming websocket data.
    Saves the latest 100 ticks for each token in the 'ltp' collection.
    """
    try:
        token = message.get('token')
        if not token or ltp_collection is None:
            return

        # Prepare the data for insertion
        document_to_insert = {
            'token': token,
            'sequence_number': message.get('sequence_number'),
            'exchange_timestamp': message.get('exchange_timestamp'),
            'last_traded_price': message.get('last_traded_price'),
            'subscription_mode': message.get('subscription_mode_val'),
            'created_at': time.time()  # Add a timestamp for sorting
        }

        # Insert the new tick data
        ltp_collection.insert_one(document_to_insert)
        print(f"Ticks: {message}")

        # Keep only the latest 100 documents for the token
        # This approach is efficient as it finds and deletes old documents in one go.
        # It triggers only when a new document is inserted for a token that already has 100 documents.
        
        # Get the count of documents for the current token
        count = ltp_collection.count_documents({'token': token})

        if count > 100:
            # Find the oldest document's id to remove
            num_to_delete = count - 100
            oldest_docs_cursor = ltp_collection.find({'token': token}).sort('created_at', ASCENDING).limit(num_to_delete)
            ids_to_delete = [doc['_id'] for doc in oldest_docs_cursor]
            
            if ids_to_delete:
                ltp_collection.delete_many({'_id': {'$in': ids_to_delete}})
                # print(f"Trimmed {len(ids_to_delete)} old entries for token {token}")

    except Exception as e:
        print(f"Error in on_data: {e}")

def on_open(wsapp):
    print("on open")
    subscribe_tokens(wsapp)

def on_error(wsapp, error):
    print(error)

def on_close(wsapp):
    print("Close")

def subscribe_tokens(wsapp):
    """
    Subscribes to the tokens fetched from MongoDB.
    """
    global sws
    tokens_to_subscribe = get_tokens_from_mongodb()
    if not tokens_to_subscribe:
        print("No tokens found to subscribe. Exiting.")
        sws.close_connection()
        return

    correlation_id = "dft_test1"
    action = 1
    mode = 1
    # Assuming exchangeType is always 2 as per the user's request
    token_list = [{"exchangeType": 2, "tokens": tokens_to_subscribe}]

    sws.subscribe(correlation_id, mode, token_list)
    print(f"Subscribed to tokens: {tokens_to_subscribe}")

# --- Main Execution ---
if __name__ == "__main__":
    # Establish connection to MongoDB first
    setup_mongodb_connection()

    # Create SmartConnect object
    obj = SmartConnect(api_key=apikey)

    # Generate session
    try:
        data = obj.generateSession(username, pwd, pyotp.TOTP(token).now())
        print(data)
        AUTH_TOKEN = data['data']['jwtToken']
        refreshToken = data['data']['refreshToken']
        FEED_TOKEN = obj.getfeedToken()
        res = obj.getProfile(refreshToken)
        print(f"Exchanges: {res['data']['exchanges']}")
    except Exception as e:
        print(f"Error during SmartAPI session generation: {e}")
        exit()

    # Initialize WebSocket
    sws = SmartWebSocketV2(AUTH_TOKEN, apikey, username, FEED_TOKEN)

    # Assign the callbacks
    sws.on_open = on_open
    sws.on_data = on_data
    sws.on_error = on_error
    sws.on_close = on_close

    # Start the websocket connection in a new thread
    threading.Thread(target=sws.connect).start()
    print('Control Released. Waiting for WebSocket to connect and subscribe...')

    # Keep the main thread alive to allow the websocket to run
    try:
        # The script will run indefinitely to keep receiving ticks.
        # You can add a condition to break the loop if needed.
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        # a graceful shutdown
        print("\nKeyboard interrupt received. Closing connection...")
        
        # Unsubscribe from all tokens before closing
        tokens_to_unsubscribe = get_tokens_from_mongodb()
        if tokens_to_unsubscribe:
            correlation_id = "dft_test1"
            mode = 1
            token_list_to_unsubscribe = [{"exchangeType": 2, "tokens": tokens_to_unsubscribe}]
            sws.unsubscribe(correlation_id, mode, token_list_to_unsubscribe)
            print(f"Unsubscribed from tokens: {tokens_to_unsubscribe}")
            time.sleep(2) # Give some time for the unsubscribe message to be sent

        sws.close_connection()
        print('Connection Closed')
