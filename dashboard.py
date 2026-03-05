import pandas as pd
import streamlit as st
import plotly.graph_objs as go
import plotly.express as px
import time 
from logic.technical_engine import(
    add_cpr_points, add_technical_parameters
)
from logic.strategy_engine import generate_signals
from logic.tracker import track_last_hit_and_profits
from data.fetch_live import get_data_from_api,fetch_latest_candles
from streamlit_autorefresh import st_autorefresh
import os
from plotly.subplots import make_subplots
import plotly.graph_objects as go

# Autorefresh the app after 5seconds
st_autorefresh(interval=5000, key="live_refresh")

css_path = os.path.join(os.path.dirname(__file__), "assets/style.css")

with open(css_path) as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Main Page
st.set_page_config(
    page_title= "BTC/USD Dashboard",
    page_icon= ":material/currency_bitcoin:",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://www.extremelycoolapp.com/help',
        'Report a bug': "https://www.extremelycoolapp.com/bug",
        'About': "# This is a header. This is an *extremely* cool app!"
    }
)

with st.container(key="app_title"):
    st.title("BTCUSDT LIVE DASHBOARD")

# SIDEBAR
st.sidebar.title("Key Metrics")
st.sidebar.markdown("---")

timeframe = st.sidebar.selectbox("Timeframe", ["5m","15m", "1h"], index=0)

state_key = f"price_df_{timeframe}"

if state_key not in st.session_state:
    df_api = get_data_from_api(timeframe)
    st.session_state[state_key] = df_api
    
df = st.session_state[state_key]

last_ts = df["timestamp"].iloc[-1]
new_df = fetch_latest_candles(timeframe, last_ts)


if new_df is not None:

    df = pd.concat([df, new_df]) \
           .drop_duplicates("timestamp") \
           .sort_values("timestamp")

    st.session_state.price_df = df

# Dataframe 
df = df.sort_values("timestamp")
cpr_df = add_cpr_points(df)
technical_df = add_technical_parameters(cpr_df)

# Layout
# st.subheader("Market Overview")
live_price,trend = st.columns([1,1])


symbol = st.sidebar.metric(
    label = "Symbol",
    value = "BTCUSDT"
)

with live_price :
    current_price = technical_df["close"].iloc[-1]
    pct_change = technical_df["price_change_pct"].iloc[-1]
    st.sidebar.metric(
        label="Live Price",
        value = f"${current_price:.2f}",
        delta = f"{pct_change:.2f}",
    )

with trend:
    st.sidebar.metric(
        label = "Trend",
        value = technical_df["trend"].iloc[-1]
    )
 # # Prices
with st.container(key="live_price_df"):
    tab1, tab2 = st.tabs(["Live Data","Technical Indicators"])
    with tab1:
        data = df.iloc[-10:,:6]
        styled_df = data.style.format({
            col: "{:.2f}" for col in data.select_dtypes("number").columns
        })
        st.dataframe(styled_df, hide_index=True)
    with tab2:
    # Technical Indicators
        st.dataframe(technical_df.iloc[:,[0]+ list(range(-5,0))].tail(10), hide_index=False)
        
st.markdown("---")
st.subheader("Price Action")
with st.container(key="price-action-options"):
    col1, col2, col3 = st.columns(3)
    with col1:
        show_cpr = st.checkbox("Pivot/CPR", value = True)
    with col2:
        show_r = st.checkbox("Resistance (R)", value = True)
    with col3:
        show_s = st.checkbox("Support (S)", value = True)
        
# CandleStick Chart
candlestick = go.Candlestick(
        x=technical_df['timestamp'],
        open=technical_df['open'],
        close = technical_df['close'],
        high = technical_df['high'],
        low = technical_df['low'],
        name = "BTCUSDT"
    )

layout = go.Layout(title=f"Candlestick Chart for BTCUSDT", 
                   xaxis=dict(title='5m Timestamp'),
                   yaxis=dict(title='Price'))
fig = go.Figure(data=[candlestick])

# CPR levels
if show_cpr:
    pivot_levels = ["pivot", "tc", "bc"]

    for level in pivot_levels:
        fig.add_trace(go.Scatter(
            x=technical_df["timestamp"],
            y=technical_df[level],
            mode="lines",
            name=level,
            line=dict(color="blue", dash="dot")
        ))

# Resistance levels
if show_r:
    res_levels = ["R1", "R2", "R3", "R4"]

    for level in res_levels:
        fig.add_trace(go.Scatter(
            x=technical_df["timestamp"],
            y=technical_df[level],
            mode="lines",
            name=level,
            line=dict(color="green", dash="dot")
        ))

# Supports levels
if show_s:
    sup_levels = ["S1", "S2", "S3", "S4"]

    for level in sup_levels:
        fig.add_trace(go.Scatter(
            x=technical_df["timestamp"],
            y=technical_df[level],
            mode="lines",
            name=level,
            line=dict(color="red", dash="dot")
        ))

# CPR Levels
latest = technical_df.iloc[-1]
st.markdown(f"""
<div class="cpr-strip">
    <div style="color:var(--sub-text); font-size:13px; margin-bottom:6px;">
        CPR INDICATORS
    </div>
    <div style="display:flex; gap:12px; flex-wrap:wrap; font-weight:500;">
        <span style="color:#3da5ff">P: {latest['pivot']:.2f}</span>
        <span style="color:#3da5ff">TC: {latest['tc']:.2f}</span>
        <span style="color:#3da5ff">BC: {latest['bc']:.2f}</span>
        <span style="color:#00e676">R1: {latest['R1']:.2f}</span>
        <span style="color:#00e676">R2: {latest['R2']:.2f}</span>
        <span style="color:#00e676">R3: {latest['R3']:.2f}</span>
        <span style="color:#00e676">R4: {latest['R4']:.2f}</span>
        <span style="color:#ff5252">S1: {latest['S1']:.2f}</span>
        <span style="color:#ff5252">S2: {latest['S2']:.2f}</span>
        <span style="color:#ff5252">S3: {latest['S3']:.2f}</span>
        <span style="color:#ff5252">S4: {latest['S4']:.2f}</span>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("#### Candlestick Chart for BTCUSDT")

fig.update_layout(
    xaxis_title="5M Timestamp",
    yaxis_title="Price",
    xaxis_rangeslider_visible=False,
    template="plotly_dark",
    paper_bgcolor="#2C2B2B",
    plot_bgcolor="#232323",
    font=dict(color="#dddddd"),
    margin=dict(l=20, r=20, t=40, b=20),
    hovermode="x unified", 
)
keep_hover=["pivot", "tc", "bc"]
for trace in fig.data:
    if trace.name not in keep_hover:
        trace.hoverinfo = "skip"
        
fig.update_xaxes(showgrid=False)
fig.update_yaxes(gridcolor="#333333")
st.plotly_chart(fig, use_container_width=True)


fig = make_subplots(
    rows=2,
    cols=1,
    shared_xaxes=True,
    vertical_spacing=0.06,
    row_heights=[0.7, 0.3],
    subplot_titles=("Price Action", "RSI (14)")
)


fig.add_trace(go.Candlestick(
    x=technical_df["timestamp"],
    open=technical_df["open"],
    high=technical_df["high"],
    low=technical_df["low"],
    close=technical_df["close"],
    name="BTCUSDT",
    increasing_line_color="#00e676",
    decreasing_line_color="#ff5252"
), row=1, col=1)

# Candlestick for Technical Analysis for BTCUSDT
# Moving Averages

fig.add_trace(go.Scatter(
    x=technical_df["timestamp"],
    y=technical_df["ema_20"],
    mode="lines",
    name="EMA 20",
    line=dict(color="#00c2ff", width=1.5)
), row=1, col=1)

fig.add_trace(go.Scatter(
    x=technical_df["timestamp"],
    y=technical_df["ema_50"],
    mode="lines",
    name="EMA 50",
    line=dict(color="#f49f17", width=1.5)
), row=1, col=1)

fig.add_trace(go.Scatter(
    x=technical_df["timestamp"],
    y=technical_df["sma"],
    mode="lines",
    name="SMA",
    line=dict(color="#9c27b0", width=1.3, dash="dot")
), row=1, col=1)

# RSI
fig.add_trace(go.Scatter(
    x=technical_df["timestamp"],
    y=technical_df["rsi"],
    mode="lines",
    name="RSI",
    line=dict(color="#ffffff", width=1.5)
), row=2, col=1)

# RSI Overbought / Oversold Lines
fig.add_hline(
    y=70,
    line_dash="dash",
    line_color="#ff5252",
    annotation_text="Overbought",
    annotation_position="top right",
    row=2,
    col=1
)

fig.add_hline(
    y=30,
    line_dash="dash",
    line_color="#00e676",
    annotation_text="Oversold",
    annotation_position="bottom right",
    row=2,
    col=1
)

# Optional RSI background zone
fig.add_hrect(
    y0=30, y1=70,
    fillcolor="rgba(255,255,255,0.03)",
    line_width=0,
    row=2, col=1
)

# Layout Styling
st.markdown("#### BTCUSDT Technical Analysis")
fig.update_layout(
    template="plotly_dark",
    paper_bgcolor="#2C2B2B",
    plot_bgcolor="#232323",
    font=dict(color="#979797"),
    margin=dict(l=20, r=20, t=60, b=30),
    hovermode="x unified",
)

fig.update_xaxes(
    showgrid=False,
    rangeslider_visible=False
)

fig.update_yaxes(
    gridcolor="#333333"
)

st.plotly_chart(fig, use_container_width=True)
# Signal Trends
# technical_df = generate_signals(technical_df)
# st.write(technical_df.tail(10))
# st.write(technical_df[technical_df["final_signal"]== "SELL"])
# latest = technical_df.iloc[-1]

# if latest["final_signal"] == "BUY":
#     st.success("🚨 BUY SIGNAL TRIGGERED")

# elif latest["final_signal"] == "SELL":
#     st.error("🚨 SELL SIGNAL TRIGGERED")
