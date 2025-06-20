import json
import threading
from typing import Dict, Optional, Callable

import redis


class RedisLTPClient:
    """
    OOP wrapper around Redis LTP cache.

    - `fetch_all()` returns a dict[token → tick dict] of all live LTPs for the configured exchange.
    - `watch(on_update, on_expire)` will call your callbacks whenever any token is set or expires.
    """

    def __init__(
        self,
        host: str = 'localhost',
        port: int = 6379,
        db: int = 0,
        exchange: int = 2,
        decode_responses: bool = True,
    ):
        self.redis = redis.Redis(
            host=host, port=port, db=db, decode_responses=decode_responses
        )
        self.exchange = exchange
        self._watch_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def _make_key(self, token: str) -> str:
        return f"ltp:{self.exchange}:{token}"

    def fetch_all(self) -> Dict[str, dict]:
        """
        Scan and return all live LTPs as a dict[token → tick dict].
        """
        cursor = 0
        pattern = f"ltp:{self.exchange}:*"
        result = {}

        while True:
            cursor, keys = self.redis.scan(cursor=cursor, match=pattern, count=100)
            for key in keys:
                raw = self.redis.get(key)
                if not raw:
                    continue
                try:
                    tick = json.loads(raw)
                    result[tick['token']] = tick
                except json.JSONDecodeError:
                    continue
            if cursor == 0:
                break

        return result

    def fetch(self, token: str) -> Optional[dict]:
        """
        Get the latest tick dict for a single token, or None if missing/expired.
        """
        key = self._make_key(token)
        raw = self.redis.get(key)
        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    def ttl(self, token: str) -> int:
        """
        Return remaining seconds before this token’s cache expires, or -2/-1 if missing/no-expiry.
        """
        return self.redis.ttl(self._make_key(token))

    def watch(
        self,
        on_update: Callable[[dict], None],
        on_expire: Callable[[str], None]
    ) -> None:
        """
        Begin watching keyspace notifications for LTP updates/expirations.
        `on_update(tick_dict)` is called on SET;
        `on_expire(token)` is called on EXPIRE.
        This method returns immediately; callbacks run in a background thread.

        **Prerequisite:** Redis must have `notify-keyspace-events Ex` enabled.
        """
        if self._watch_thread and self._watch_thread.is_alive():
            raise RuntimeError("Already watching")

        self._stop_event.clear()
        pubsub = self.redis.pubsub()
        channel = f"__keyspace@{self.redis.connection_pool.connection_kwargs['db']}__:" \
                  f"ltp:{self.exchange}:*"
        pubsub.psubscribe(channel)

        def _run():
            for msg in pubsub.listen():
                if self._stop_event.is_set():
                    break
                if msg['type'] != 'pmessage':
                    continue

                full_key = msg['channel'].split(b':', 2)[-1].decode()
                action = msg['data'].decode()

                if action == 'set':
                    raw = self.redis.get(full_key)
                    if not raw:
                        continue
                    try:
                        tick = json.loads(raw)
                        on_update(tick)
                    except json.JSONDecodeError:
                        continue
                elif action == 'expire':
                    token = full_key.rsplit(':', 1)[-1]
                    on_expire(token)

            pubsub.close()

        self._watch_thread = threading.Thread(target=_run, daemon=True)
        self._watch_thread.start()

    def stop_watch(self) -> None:
        """
        Signal the watch thread to stop.
        """
        if self._watch_thread and self._watch_thread.is_alive():
            self._stop_event.set()
            self._watch_thread.join()
