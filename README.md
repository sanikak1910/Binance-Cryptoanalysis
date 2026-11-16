## BTCUSDT Live Analytics
A Python and Streamlit application for monitoring cryptocurrency market data and visualizing technical indicators.

### 1. Project Objective
The objective of the BTCUSDT Live Market Analytics Dashboard is to develop an interactive application that retrieves cryptocurrency market data, processes price and volume information, calculates technical indicators, and presents market conditions in a clear visual format.

### 2. Project Description
The application is built with Python and Streamlit, with Plotly used for interactive financial charts. Market data is obtained through Binance API endpoints. The data is cleaned, ordered by timestamp, and updated incrementally. Technical-analysis functions calculate Central Pivot Range (CPR), support and resistance levels, and moving-average and momentum indicators. The dashboard presents these calculations alongside candlestick, volume, and RSI visualizations.

The current implementation is a market-monitoring and analysis tool.Strategy signals, backtesting, paper trading, and machine-learning predictions are proposed extensions.

### Current dashboard features

  * Timeframe selector for 5-minute, 15-minute, and 1-hour candles.
  * Market summary metrics: latest price, 24-hour change, high, low, and volume.
  * Candlestick price-action chart with optional CPR, resistance, and support overlays.
  * EMA 20, EMA 50, and SMA overlays.
  * Volume chart and RSI chart.
  * Live-data and technical-indicator tables.
  * Candle data strip showing OHLC and selected CPR levels.
