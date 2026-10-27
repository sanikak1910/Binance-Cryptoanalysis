import logging
import os

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from data.fetch_live import (
    get_data_from_api,
    fetch_latest_candles,
    update_candle,
    merge_candles,
)
from data.websocket_client import BinanceKlineFeed
from logic.technical_engine import (
    add_cpr_points,
    add_technical_parameters,
)

# =========================================================
# CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="Live Crypto Trading Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SYMBOL = "BTCUSDT"
TIMEFRAMES = ["5m", "15m", "1h"]
CANDLES_PER_DAY = {"5m": 288, "15m": 96, "1h": 24}
MAX_CANDLES = 2000

# =========================================================
# LOAD DARK THEME CSS
# =========================================================

css_path = os.path.join(
    os.path.dirname(__file__), "assets", "style.css"
)

if os.path.exists(css_path):
    with open(css_path, encoding="utf-8") as file:
        st.markdown(
            f"<style>{file.read()}</style>",
            unsafe_allow_html=True,
        )


# =========================================================
# HELPER FUNCTIONS
# =========================================================


def show_connection_status(status):
    """Display a floating WebSocket connection badge in the top-right corner."""

    if isinstance(status, dict):
        # Handle the actual dictionary returned by BinanceKlineFeed
        if status.get("connected") is True:
            status = "connected"
        elif status.get("last_error"):
            status = "error"
        else:
            status = (
                status.get("status")
                or status.get("state")
                or status.get("connection_status")
                or "disconnected"
            )

    status = str(status).strip().lower()

    if status in ("connected", "open", "running"):
        css_class = "connection-connected"
        message = "WebSocket Connected"

    elif status in ("connecting",):
        css_class = "connection-disconnected"
        message = "WebSocket Connecting..."

    elif status in ("disconnected", "closed", "stopped"):
        css_class = "connection-disconnected"
        message = "WebSocket Disconnected"

    else:
        css_class = "connection-error"
        message = "WebSocket Status Unavailable"

    st.markdown(
        f"""
        <div class="connection-status {css_class}">
            <span class="connection-dot"></span>
            <span>{message}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

def calculate_price_change(df, timeframe):
    candles = CANDLES_PER_DAY[timeframe]

    if len(df) <= candles:
        previous_price = float(df["close"].iloc[0])
    else:
        previous_price = float(df["close"].iloc[-candles - 1])

    current_price = float(df["close"].iloc[-1])

    if previous_price == 0:
        return 0.0

    return (current_price / previous_price - 1) * 100

def create_price_chart(
    df,
    show_cpr=True,
    show_resistance=True,
    show_support=True,
    show_ema=True,
):
    fig = go.Figure()

    # Candlestick chart
    fig.add_trace(
        go.Candlestick(
            x=df["timestamp"],
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name=SYMBOL,
            increasing_line_color="#22c55e",
            decreasing_line_color="#ef4444",
        )
    )

    # CPR levels
    if show_cpr:
        for col, color in [
            ("pivot", "#60a5fa"),
            ("tc", "#a78bfa"),
            ("bc", "#f59e0b"),
        ]:
            if col in df.columns:
                fig.add_trace(
                    go.Scatter(
                        x=df["timestamp"],
                        y=df[col],
                        mode="lines",
                        name=col.upper(),
                        line=dict(
                            color=color,
                            width=1.2,
                            dash="dot",
                        ),
                    )
                )

    # Resistance levels
    if show_resistance:
        for level in ["R1", "R2", "R3", "R4"]:
            if level in df.columns:
                fig.add_trace(
                    go.Scatter(
                        x=df["timestamp"],
                        y=df[level],
                        mode="lines",
                        name=level,
                        line=dict(
                            color="#22c55e",
                            width=1,
                            dash="dot",
                        ),
                    )
                )

    # Support levels
    if show_support:
        for level in ["S1", "S2", "S3", "S4"]:
            if level in df.columns:
                fig.add_trace(
                    go.Scatter(
                        x=df["timestamp"],
                        y=df[level],
                        mode="lines",
                        name=level,
                        line=dict(
                            color="#f87171",
                            width=1,
                            dash="dot",
                        ),
                    )
                )


    fig.update_layout(
        title=f"{SYMBOL} Price Chart",
        template="plotly_dark",
        paper_bgcolor="#111827",
        plot_bgcolor="#111827",
        font=dict(color="#e2e8f0"),
        height=600,
        xaxis_title="Time",
        yaxis_title="Price (USDT)",
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
        margin=dict(l=15, r=15, t=60, b=15),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
    )

    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="#263449", zeroline=False)

    return fig

def create_volume_chart(df):
    colors = [
        "#22c55e" if close >= open_price else "#ef4444"
        for open_price, close in zip(df["open"], df["close"])
    ]

    fig = go.Figure(
        go.Bar(
            x=df["timestamp"],
            y=df["volume"],
            marker_color=colors,
            name="Volume",
        )
    )

    fig.update_layout(
        title="Trading Volume",
        template="plotly_dark",
        paper_bgcolor="#111827",
        plot_bgcolor="#111827",
        font=dict(color="#e2e8f0"),
        height=300,
        xaxis_title="Time",
        yaxis_title="Volume",
        margin=dict(l=15, r=15, t=50, b=15),
    )

    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="#263449")

    return fig

def create_moving_average_chart(df):
    fig = go.Figure()

    # Closing price
    fig.add_trace(
        go.Scatter(
            x=df["timestamp"],
            y=df["close"],
            mode="lines",
            name="Close Price",
            line=dict(color="#e2e8f0", width=1.5),
        )
    )

    # EMA 20
    if "ema_20" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df["timestamp"],
                y=df["ema_20"],
                mode="lines",
                name="EMA 20",
                line=dict(color="#38bdf8", width=2),
            )
        )

    # EMA 50
    if "ema_50" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df["timestamp"],
                y=df["ema_50"],
                mode="lines",
                name="EMA 50",
                line=dict(color="#f59e0b", width=2),
            )
        )

    # SMA
    if "sma" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df["timestamp"],
                y=df["sma"],
                mode="lines",
                name="SMA",
                line=dict(color="#c084fc", width=2),
            )
        )

    fig.update_layout(
        title="Moving Average Analysis — EMA & SMA",
        template="plotly_dark",
        paper_bgcolor="#111827",
        plot_bgcolor="#111827",
        font=dict(color="#e2e8f0"),
        height=420,
        xaxis_title="Time",
        yaxis_title="Price (USDT)",
        hovermode="x unified",
        margin=dict(l=15, r=15, t=60, b=15),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
    )

    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="#263449", zeroline=False)

    return fig

# def render_candle_summary(df):
    latest = df.iloc[-1]

    levels = [
        ("Open", "open"),
        ("High", "high"),
        ("Low", "low"),
        ("Close", "close"),
        ("Pivot", "pivot"),
        ("TC", "tc"),
        ("BC", "bc"),
        ("R1", "R1"),
        ("R2", "R2"),
        ("S1", "S1"),
        ("S2", "S2"),
    ]

    items = []

    for label, column in levels:
        if column in df.columns and pd.notna(latest[column]):
            items.append(
                f"""
                <div class="candle-chip">
                    <span>{label}</span>
                    <strong>{float(latest[column]):,.2f}</strong>
                </div>
                """
            )

    st.markdown(
        '<div class="candle-strip">'
        + "".join(items)
        + "</div>",
        unsafe_allow_html=True,
    )


# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.title("Dashboard Settings")

timeframe = st.sidebar.selectbox(
    "Select Timeframe",
    TIMEFRAMES,
    index=0,
)

st.sidebar.markdown(f"**Symbol:** {SYMBOL}")
st.sidebar.markdown("**Data Source:** Binance")
st.sidebar.caption("Historical data: REST API")
st.sidebar.caption("Live updates: WebSocket")
st.sidebar.caption("Charts use the selected timeframe.")

# =========================================================
# SESSION STATE
# =========================================================

if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame()

if "feed" not in st.session_state:
    st.session_state.feed = None

if "active_timeframe" not in st.session_state:
    st.session_state.active_timeframe = None

if "last_connection_id" not in st.session_state:
    st.session_state.last_connection_id = None


# =========================================================
# INITIALIZE DATA AND WEBSOCKET
# =========================================================

if st.session_state.active_timeframe != timeframe:
    old_feed = st.session_state.feed

    if old_feed is not None:
        try:
            old_feed.stop()
        except Exception:
            logger.exception("Could not stop previous feed")

    try:
        with st.spinner("Loading historical candles..."):
            initial_df = get_data_from_api(
                symbol=SYMBOL,
                interval=timeframe,
                days=7,
            )

        if initial_df is None or initial_df.empty:
            st.session_state.df = pd.DataFrame()
        else:
            st.session_state.df = (
                initial_df.tail(MAX_CANDLES).reset_index(drop=True)
            )

        feed = BinanceKlineFeed(
            symbol=SYMBOL,
            interval=timeframe,
        )
        feed.start()

        st.session_state.feed = feed
        st.session_state.active_timeframe = timeframe
        st.session_state.last_connection_id = None

    except Exception as exc:
        logger.exception("Initialization failed")
        st.error(f"Unable to initialize dashboard: {exc}")
        st.stop()


# =========================================================
# DASHBOARD HEADER
# =========================================================

st.markdown(
    """
    <div class="dashboard-header">
        <div class="eyebrow">LIVE MARKET MONITORING</div>
        <h1>📈 Live Crypto Trading Dashboard</h1>
        <p>
            Real-time BTCUSDT price action, technical indicators,
            support/resistance levels and market data.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.divider()


# =========================================================
# LIVE DASHBOARD
# =========================================================

@st.fragment(run_every="5s")
def live_dashboard():

    feed = st.session_state.feed

    if feed is None:
        show_connection_status("disconnected")
        st.caption("WebSocket feed is not initialized.")
        return

    # ---------------- CONNECTION STATUS ----------------
    print("Status:", feed.get_status())
    try:
        status = feed.get_status()
    except Exception:
        logger.exception("Unable to read WebSocket status")
        status = "error"

    show_connection_status(status)

    # Normalize status and extract reconnect ID if available.
    if isinstance(status, dict):
        connection_id = status.get("connection_id")
    else:
        connection_id = None

    # ---------------- RECOVER MISSED CANDLES ----------------

    if (
        connection_id is not None
        and connection_id != st.session_state.last_connection_id
        and not st.session_state.df.empty
    ):
        try:
            last_timestamp = st.session_state.df["timestamp"].iloc[-1]

            recovered = fetch_latest_candles(
                symbol=SYMBOL,
                interval=timeframe,
                last_timestamp=last_timestamp,
            )

            if recovered is not None and not recovered.empty:
                st.session_state.df = merge_candles(
                    st.session_state.df,
                    recovered,
                )

            st.session_state.last_connection_id = connection_id

        except Exception:
            logger.exception("Could not recover missed candles")

    # ---------------- PROCESS WEBSOCKET EVENTS ----------------

    try:
        events = feed.get_events()
    except Exception:
        logger.exception("Unable to read WebSocket events")
        events = []

    for event in events or []:
        try:
            st.session_state.df = update_candle(
                st.session_state.df,
                event,
            )
        except Exception:
            logger.exception("Candle update failed")

    df = st.session_state.df

    if df is None or df.empty:
        st.info("Waiting for market data...")
        return

    df = df.tail(MAX_CANDLES).reset_index(drop=True)
    st.session_state.df = df

    # ---------------- TECHNICAL INDICATORS ----------------

    try:
        technical_df = add_technical_parameters(
            add_cpr_points(df.copy())
        )
    except Exception:
        logger.exception("Indicator calculation failed")
        technical_df = df.copy()

    # ---------------- METRICS ----------------

    current_price = float(df["close"].iloc[-1])
    latest_volume = float(df["volume"].iloc[-1])

    candles_24h = min(CANDLES_PER_DAY[timeframe], len(df))

    high_24h = float(df["high"].tail(candles_24h).max())
    low_24h = float(df["low"].tail(candles_24h).min())

    price_change = calculate_price_change(df, timeframe)

    # Compact, equal-width metric cards.
    columns = st.columns(5, gap="small")

    columns[0].metric(
        "Current Price",
        f"${current_price:,.2f}",
    )

    columns[1].metric(
        "24H High*",
        f"${high_24h:,.2f}",
    )

    columns[2].metric(
        "24H Low*",
        f"${low_24h:,.2f}",
    )

    columns[3].metric(
        "Latest Candle Volume",
        f"{latest_volume:,.2f}",
    )

    columns[4].metric(
        "Candles Loaded",
        f"{len(df):,}",
    )

    st.caption(
        f"Approx. price change: {price_change:+.2f}% | "
        "*High/low are based on candles currently loaded."
    )

    # =====================================================
    # TWO MAIN TABS
    # =====================================================

    charts_tab, data_tab = st.tabs(
        ["📊 Charts", "🧾 Dataframes"]
    )

    # =====================================================
    # TAB 1 — CHARTS
    # =====================================================

    with charts_tab:

        st.subheader("Price Chart Controls")

        col1, col2, col3, col4 = st.columns(4)

        show_cpr = col1.checkbox(
            "Show CPR",
            value=True,
            key=f"cpr_{timeframe}",
        )

        show_resistance = col2.checkbox(
            "Show Resistance",
            value=True,
            key=f"resistance_{timeframe}",
        )

        show_support = col3.checkbox(
            "Show Support",
            value=True,
            key=f"support_{timeframe}",
        )

        show_ema = col4.checkbox(
            "Show Moving Averages",
            value=True,
            key=f"ema_{timeframe}",
        )

        st.subheader("BTCUSDT Price Action")

        price_fig = create_price_chart(
            technical_df,
            show_cpr=show_cpr,
            show_resistance=show_resistance,
            show_support=show_support,
            show_ema=show_ema,
        )

        st.plotly_chart(
            price_fig,
            key=f"price_chart_{timeframe}",
        )

        
        st.subheader("EMA & SMA Analysis")

        ma_fig = create_moving_average_chart(technical_df)

        st.plotly_chart(
            ma_fig,
            key=f"moving_average_chart_{timeframe}",
        )

        st.subheader("Trading Volume")

        volume_fig = create_volume_chart(df)

        st.plotly_chart(
            volume_fig,
            key=f"volume_chart_{timeframe}",
        )

        # st.subheader("Latest Candle Snapshot")
        # render_candle_summary(technical_df)

    # =====================================================
    # TAB 2 — DATAFRAMES
    # =====================================================

    with data_tab:

        st.subheader("Latest 100 Candles")

        latest_data = technical_df.tail(100).sort_values(
            "timestamp",
            ascending=False,
        )

        st.dataframe(
            latest_data,
            hide_index=True,
        )

        st.divider()

        st.subheader("Complete Loaded Dataset")

        st.caption(
            f"{len(technical_df):,} candles currently retained in memory."
        )

        full_data = technical_df.sort_values(
            "timestamp",
            ascending=False,
        )

        st.dataframe(
            full_data,
            hide_index=True,
        )

        csv_data = full_data.to_csv(index=False).encode("utf-8")

        st.download_button(
            "Download Data as CSV",
            data=csv_data,
            file_name=f"{SYMBOL}_{timeframe}_candles.csv",
            mime="text/csv",
            key=f"download_{timeframe}",
        )


live_dashboard()

# =========================================================
# SIDEBAR FOOTER
# =========================================================

st.sidebar.divider()
st.sidebar.caption("Binance market data")
st.sidebar.caption("Historical candles via REST API")
st.sidebar.caption("Live updates via WebSocket")
st.sidebar.caption("For educational purposes only.")