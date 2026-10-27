from datetime import datetime

import pandas as pd
from binance.client import Client


TIMEZONE = "Asia/Kolkata"

CANDLE_COLUMNS = [
    "timestamp",
    "open",
    "high",
    "low",
    "close",
    "volume",
]


def get_binance_client():
    """
    Create a Binance client.

    Public market data does not require API keys.
    """
    return Client()


def klines_to_df(klines):
    """
    Convert Binance REST kline data into a DataFrame.

    Binance kline fields:
    0: open time
    1: open
    2: high
    3: low
    4: close
    5: volume
    """

    if not klines:
        return pd.DataFrame(columns=CANDLE_COLUMNS)

    df = pd.DataFrame(
        klines,
        columns=[
            "open_time",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
            "quote_asset_volume",
            "number_of_trades",
            "taker_buy_base_asset_volume",
            "taker_buy_quote_asset_volume",
            "ignore",
        ],
    )

    df = df[
        [
            "open_time",
            "open",
            "high",
            "low",
            "close",
            "volume",
        ]
    ].copy()

    df.rename(
        columns={"open_time": "timestamp"},
        inplace=True,
    )

    # Convert Binance UTC milliseconds to India time.
    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        unit="ms",
        utc=True,
    )

    df["timestamp"] = (
        df["timestamp"]
        .dt.tz_convert(TIMEZONE)
        .dt.tz_localize(None)
    )

    numeric_columns = [
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

    df = df.dropna(subset=CANDLE_COLUMNS)

    df = (
        df.sort_values("timestamp")
        .drop_duplicates(subset=["timestamp"], keep="last")
        .reset_index(drop=True)
    )

    return df[CANDLE_COLUMNS]


def get_data_from_api(
    symbol="BTCUSDT",
    interval="5m",
    days=7,
):
    """
    Fetch historical candles from Binance REST API.
    """

    client = get_binance_client()

    start_str = f"{days} days ago UTC"

    klines = client.get_historical_klines(
        symbol=symbol,
        interval=interval,
        start_str=start_str,
    )

    return klines_to_df(klines)


def update_candle(df, candle):
    """
    Update an existing candle or append a new candle from WebSocket data.

    candle format:
    {
        "timestamp": Binance UTC timestamp in milliseconds,
        "open": float,
        "high": float,
        "low": float,
        "close": float,
        "volume": float,
        "is_closed": bool
    }
    """

    if df is None or df.empty:
        df = pd.DataFrame(columns=CANDLE_COLUMNS)

    df = df.copy()

    candle_timestamp = pd.to_datetime(
        candle["timestamp"],
        unit="ms",
        utc=True,
    )

    candle_timestamp = (
        candle_timestamp
        .tz_convert(TIMEZONE)
        .tz_localize(None)
    )

    new_row = {
        "timestamp": candle_timestamp,
        "open": float(candle["open"]),
        "high": float(candle["high"]),
        "low": float(candle["low"]),
        "close": float(candle["close"]),
        "volume": float(candle["volume"]),
    }

    if df.empty:
        df = pd.DataFrame([new_row])

    else:
        matching_rows = (
            df["timestamp"] == candle_timestamp
        )

        if matching_rows.any():
            # Replace the current candle with the latest WebSocket values.
            df.loc[matching_rows, CANDLE_COLUMNS] = [
                new_row[column]
                for column in CANDLE_COLUMNS
            ]

        else:
            # A new candle has started.
            df = pd.concat(
                [
                    df,
                    pd.DataFrame([new_row]),
                ],
                ignore_index=True,
            )

    df = (
        df.sort_values("timestamp")
        .drop_duplicates(subset=["timestamp"], keep="last")
        .reset_index(drop=True)
    )

    return df[CANDLE_COLUMNS]


def merge_candles(existing_df, new_df):
    """
    Merge REST recovery candles with existing dashboard data.
    """

    if existing_df is None or existing_df.empty:
        if new_df is None or new_df.empty:
            return pd.DataFrame(columns=CANDLE_COLUMNS)

        return new_df[CANDLE_COLUMNS].copy()

    if new_df is None or new_df.empty:
        return existing_df[CANDLE_COLUMNS].copy()

    merged = pd.concat(
        [
            existing_df[CANDLE_COLUMNS],
            new_df[CANDLE_COLUMNS],
        ],
        ignore_index=True,
    )

    merged = (
        merged.sort_values("timestamp")
        .drop_duplicates(subset=["timestamp"], keep="last")
        .reset_index(drop=True)
    )

    return merged[CANDLE_COLUMNS]


def fetch_latest_candles(
    symbol,
    interval,
    last_timestamp,
    limit=1000,
):
    """
    Fetch candles after last_timestamp for recovery.

    last_timestamp is expected to be timezone-naive India time,
    matching the timestamp column in the dashboard DataFrame.
    """

    if last_timestamp is None:
        return pd.DataFrame(columns=CANDLE_COLUMNS)

    timestamp = pd.Timestamp(last_timestamp)

    if timestamp.tzinfo is None:
        timestamp = timestamp.tz_localize(TIMEZONE)
    else:
        timestamp = timestamp.tz_convert(TIMEZONE)

    # Convert to UTC milliseconds for Binance.
    start_time_ms = (
        timestamp
        .tz_convert("UTC")
        .timestamp()
        * 1000
    )

    # Start slightly after the last known candle open time.
    start_time_ms = int(start_time_ms) + 1

    client = get_binance_client()

    klines = client.get_klines(
        symbol=symbol,
        interval=interval,
        startTime=start_time_ms,
        limit=limit,
    )

    return klines_to_df(klines)

