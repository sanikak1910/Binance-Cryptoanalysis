import json
import logging
import threading
import time
from queue import Empty, Queue

import websocket

logger = logging.getLogger(__name__)


class BinanceKlineFeed:

    # Port 443 is often more accessible on restricted networks.
    BASE_URL = "wss://stream.binance.com:443/ws"

    def __init__(self, symbol: str, interval: str):
        self.symbol = symbol.lower()
        self.interval = interval

        self.stream_url = (
            f"{self.BASE_URL}/"
            f"{self.symbol}@kline_{self.interval}"
        )

        self.queue = Queue()

        self.ws = None
        self._thread = None

        self._stop_event = threading.Event()
        self._connected_event = threading.Event()

        self._status_lock = threading.Lock()

        self._connection_id = 0
        self._last_error = None

    def start(self):
        """Start WebSocket in a background thread."""

        if self._thread and self._thread.is_alive():
            return

        self._stop_event.clear()

        self._thread = threading.Thread(
            target=self._run,
            daemon=True,
            name=f"BinanceWS-{self.symbol}-{self.interval}",
        )

        self._thread.start()

    def _run(self):
        """Connect and reconnect automatically."""

        reconnect_delay = 1
        max_reconnect_delay = 30

        while not self._stop_event.is_set():

            try:
                logger.info(
                    "Connecting to Binance: %s",
                    self.stream_url,
                )

                self.ws = websocket.WebSocketApp(
                    self.stream_url,
                    on_open=self._on_open,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close,
                )

                self.ws.run_forever(
                    ping_interval=20,
                    ping_timeout=10,
                )

            except Exception as exc:
                self._set_error(str(exc))
                logger.exception("WebSocket connection failed")

            self._connected_event.clear()

            if self._stop_event.is_set():
                break

            logger.warning(
                "Disconnected. Retrying in %s seconds.",
                reconnect_delay,
            )

            time.sleep(reconnect_delay)

            reconnect_delay = min(
                reconnect_delay * 2,
                max_reconnect_delay,
            )

    def _on_open(self, ws):
        """Called when connection opens."""

        self._connected_event.set()

        with self._status_lock:
            self._connection_id += 1
            self._last_error = None

        logger.info(
            "Binance WebSocket connected: %s",
            self.stream_url,
        )

    def _on_message(self, ws, message):
        """Parse and queue kline events."""

        try:
            payload = json.loads(message)

            candle = payload.get("k")

            if not candle:
                return

            event = {
                "timestamp": int(candle["t"]),
                "open": float(candle["o"]),
                "high": float(candle["h"]),
                "low": float(candle["l"]),
                "close": float(candle["c"]),
                "volume": float(candle["v"]),
                "is_closed": bool(candle["x"]),
            }

            self.queue.put(event)

        except Exception as exc:
            self._set_error(
                f"Could not parse WebSocket message: {exc}"
            )

            logger.exception("Message parsing error")

    def _on_error(self, ws, error):
        """Called when WebSocket encounters an error."""

        self._connected_event.clear()
        self._set_error(str(error))

        logger.error(
            "Binance WebSocket error: %s",
            error,
        )

    def _on_close(self, ws, close_status_code, close_msg):
        """Called when WebSocket closes."""

        self._connected_event.clear()

        logger.warning(
            "WebSocket closed. Code=%s, Message=%s",
            close_status_code,
            close_msg,
        )

    def _set_error(self, error):
        with self._status_lock:
            self._last_error = error

    def get_events(self):
        """Return all events currently in the queue."""

        events = []

        while True:
            try:
                events.append(
                    self.queue.get_nowait()
                )
            except Empty:
                break

        return events

    def get_status(self):
        """Return connection status."""

        with self._status_lock:
            return {
                "connected": self._connected_event.is_set(),
                "connection_id": self._connection_id,
                "last_error": self._last_error,
            }

    def stop(self):
        """Close the connection and stop the thread."""

        self._stop_event.set()
        self._connected_event.clear()

        if self.ws:
            try:
                self.ws.close()
            except Exception:
                logger.exception(
                    "Error while closing WebSocket"
                )

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3)