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
sws = None

def get_tokens_from_mongodb():
    """
    Fetches the list of tokens from the 'master' collection in MongoDB.
    """
    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        master_collection = db[MASTER_COLLECTION]
        # Fetches tokens where exch_seg is 'NFO' as their exchangeType is 2
        tokens = [doc['token'] for doc in master_collection.find({'exch_seg': 'NFO'}, {'token': 1, '_id': 0})]
        client.close()
        print(f"Successfully fetched {len(tokens)} NFO tokens from the 'master' collection.")
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
        count = ltp_collection.count_documents({'token': token})

        if count > 100:
            num_to_delete = count - 100
            # Find the oldest documents' ids to remove
            oldest_docs_cursor = ltp_collection.find({'token': token}).sort('created_at', ASCENDING).limit(num_to_delete)
            ids_to_delete = [doc['_id'] for doc in oldest_docs_cursor]
            
            if ids_to_delete:
                ltp_collection.delete_many({'_id': {'$in': ids_to_delete}})
                # print(f"Trimmed {len(ids_to_delete)} old entries for token {token}")

    except Exception as e:
        print(f"Error in on_data: {e}")

def on_open(wsapp):
    print("on open")
    subscribe_tokens()

def on_error(wsapp, error):
    print(error)

def on_close(wsapp):
    print("Close")

def subscribe_tokens():
    """
    Subscribes to the tokens fetched from MongoDB and the additional hardcoded token.
    """
    global sws
    correlation_id = "dft_stream"
    action = 1
    mode = 1
    
    # --- Subscription for tokens from MongoDB ---
    tokens_to_subscribe_mongo = get_tokens_from_mongodb()
    if tokens_to_subscribe_mongo:
        # Assuming exchangeType is always 2 for tokens from MongoDB as per the initial request
        token_list_1 = [{"exchangeType": 2, "tokens": tokens_to_subscribe_mongo}]
        sws.subscribe(correlation_id, mode, token_list_1)
        print(f"Subscribed to tokens from MongoDB: {tokens_to_subscribe_mongo}")
    else:
        print("No NFO tokens found in MongoDB to subscribe.")

    # --- Subscription for the hardcoded token ---
    token_list_2 = [{"exchangeType": 1, "tokens": ["26000"]}]
    sws.subscribe(correlation_id, mode, token_list_2)
    print("Subscribed to hardcoded token: 26000 with exchangeType: 1")


# --- Main Execution ---
if __name__ == "__main__":
    # Establish connection to MongoDB first
    setup_mongodb_connection()

    # Create SmartConnect object
    obj = SmartConnect(api_key=apikey)

    # Generate session
    try:
        data = obj.generateSession(username, pwd, pyotp.TOTP(token).now())
        print("Session Generated Successfully")
        AUTH_TOKEN = data['data']['jwtToken']
        refreshToken = data['data']['refreshToken']
        FEED_TOKEN = obj.getfeedToken()
        res = obj.getProfile(refreshToken)
        print(f"Exchanges Available: {res['data']['exchanges']}")
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
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nKeyboard interrupt received. Unsubscribing and closing connection...")
        correlation_id = "dft_stream"
        mode = 1
        
        # Unsubscribe from MongoDB tokens
        tokens_to_unsubscribe_mongo = get_tokens_from_mongodb()
        if tokens_to_unsubscribe_mongo:
            token_list_1_unsub = [{"exchangeType": 2, "tokens": tokens_to_unsubscribe_mongo}]
            sws.unsubscribe(correlation_id, mode, token_list_1_unsub)
            print(f"Unsubscribed from MongoDB tokens: {tokens_to_unsubscribe_mongo}")

        # Unsubscribe from the hardcoded token
        token_list_2_unsub = [{"exchangeType": 1, "tokens": ["26000"]}]
        sws.unsubscribe(correlation_id, mode, token_list_2_unsub)
        print("Unsubscribed from hardcoded token: 26000")

        time.sleep(2) # Give some time for the unsubscribe messages to be sent

        sws.close_connection()
        print('Connection Closed')
