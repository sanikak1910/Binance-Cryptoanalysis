from binance.client import Client
import pandas as pd
from datetime import datetime, timedelta, timezone

# -----------------------------
# Initialize Binance Client
# (No API key required for public data)
# -----------------------------
client = Client()

# -----------------------------
# Interval Map
# -----------------------------
INTERVAL_MAP = {
    "5m": Client.KLINE_INTERVAL_5MINUTE,
    "15m": Client.KLINE_INTERVAL_15MINUTE,
    "1h": Client.KLINE_INTERVAL_1HOUR
}

# -----------------------------
# Get 7 days historical data
# -----------------------------
def get_data_from_api(timeframe):

    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=7)

    start_ms = int(start_time.timestamp() * 1000)
    end_ms = int(end_time.timestamp() * 1000)

    all_klines = []
    limit = 1000
    fetch_start = start_ms

    while True:
        klines = client.get_klines(
            symbol="BTCUSDT",
            interval=INTERVAL_MAP[timeframe],
            startTime=fetch_start,
            endTime=end_ms,
            limit=limit
        )

        if not klines:
            break

        all_klines.extend(klines)
        last_open_time = klines[-1][0]

        # Move forward to avoid duplicates
        fetch_start = last_open_time + 1

        if last_open_time >= end_ms:
            break

    return klines_to_df(all_klines)


# -----------------------------
# Fetch new candles after last timestamp
# -----------------------------
def fetch_latest_candles(timeframe, last_ts):

    start_ms = int(last_ts.timestamp() * 1000) + 1

    klines = client.get_historical_klines(
        symbol="BTCUSDT",
        interval=INTERVAL_MAP[timeframe],
        start_str=start_ms
    )

    if not klines:
        return None

    return klines_to_df(klines)


# -----------------------------
# Convert Klines to DataFrame
# -----------------------------
def klines_to_df(klines):

    df_sample = pd.DataFrame(klines, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_asset_volume', 'num_trades',
        'taker_buy_base', 'taker_buy_quote', 'ignore'
    ])

    df_sample = df_sample.iloc[:, :6]

    df_sample['timestamp'] = (
        pd.to_datetime(df_sample['timestamp'], unit='ms')
        .dt.tz_localize('UTC')
        .dt.tz_convert('Asia/Kolkata')
        .dt.tz_localize(None)
    )

    df_sample[['open', 'close', 'low', 'high', 'volume']] = \
        df_sample[['open', 'close', 'low', 'high', 'volume']].astype(float)

    return df_sample