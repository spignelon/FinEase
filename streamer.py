import threading
import time
import json
import redis
from SmartApi import SmartConnect
from SmartApi.smartWebSocketV2 import SmartWebSocketV2
import pyotp


class LTPRedisCache:
    """
    Caches latest LTP per token in Redis with a 60-second TTL.
    Key format:   ltp:<exchange_type>:<token>
    Value format: JSON string of the tick dict.
    """

    def __init__(self, host='localhost', port=6379, db=0, ttl=60):
        self.redis = redis.Redis(host=host, port=port, db=db, decode_responses=True)
        self.ttl = ttl

    def save_tick(self, tick: dict):
        exchange = tick['exchange_type']
        token    = tick['token']
        key      = f"ltp:{exchange}:{token}"
        value    = json.dumps(tick)
        # Overwrite the key each time, and reset TTL to self.ttl
        self.redis.set(key, value, ex=self.ttl)


class SmartLTPStreamer:
    """
    Handles SmartAPI login, websocket connection, and feeds ticks into a LTPRedisCache.
    """

    def __init__(self, api_key, username, password, totp_token, tokens: list, exchange_type: int):
        # SmartAPI login
        self.client = SmartConnect(api_key=api_key)
        session = self.client.generateSession(username, password, totp_token)
        auth = session['data']
        self.auth_token  = auth['jwtToken']
        self.refresh     = auth['refreshToken']
        self.feed_token  = self.client.getfeedToken()
        self.tokens      = tokens
        self.exchange    = exchange_type

        # Prepare Redis cache
        self.cache = LTPRedisCache()

        # Prepare WebSocket
        self.sws = SmartWebSocketV2(self.auth_token, api_key, username, self.feed_token)
        self.sws.on_open  = self._on_open
        self.sws.on_data  = self._on_data
        self.sws.on_error = self._on_error
        self.sws.on_close = self._on_close

    def _on_open(self, ws):
        print("WebSocket opened, subscribing to tokens…")
        correlation_id = "ltp_stream"
        mode = 1  # LTP mode
        tlist = [{"exchangeType": self.exchange, "tokens": self.tokens}]
        self.sws.subscribe(correlation_id, mode, tlist)

    def _on_data(self, ws, message):
        """
        Called on every incoming tick. We parse it and push into Redis.
        """
        # message already a dict
        tick = message
        if tick.get('last_traded_price') is not None:
            self.cache.save_tick(tick)
            print(f"Cached token {tick['token']} @ {tick['last_traded_price']}")

    def _on_error(self, ws, error):
        print("WebSocket error:", error)

    def _on_close(self, ws):
        print("WebSocket closed")

    def start(self):
        """
        Starts the WebSocket in its own thread.
        """
        threading.Thread(target=self.sws.connect, daemon=True).start()

    def stop(self):
        """
        Gracefully closes the WebSocket connection.
        """
        self.sws.close_connection()


if __name__ == '__main__':
    # --- CONFIGURE THESE ---
    from config import apikey, username, pwd, token  # your SmartAPI creds

    # large list of tokens, all for exchange type 2
    tokens = ["50850", "50863", "50900", "50942"]
    exchange_type = 2


    
    streamer = SmartLTPStreamer(
        api_key=apikey,
        username=username,
        password=pwd,
        totp_token=pyotp.TOTP(token).now(),
        tokens=tokens,
        exchange_type=exchange_type
    )
    streamer.start()

    print("Streamer running—press Ctrl+C to exit.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        streamer.stop()
        print("Exited.")
