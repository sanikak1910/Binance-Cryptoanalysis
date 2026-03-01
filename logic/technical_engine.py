import pandas as pd
import numpy as np

# Calculate CPR values
def apply_pivot_levels(df, prev_high, prev_low, prev_close):
    # Calculate Pivot Point (P)
    P = (prev_high +  prev_low  +  prev_close ) / 3

    bc1 = ( prev_high  +  prev_low ) / 2
    tc1 = 2 * P - bc1
    
    BC = np.minimum(bc1, tc1)
    TC = np.maximum(bc1, tc1)
    
    # Calculate support and resistance levels
    R1 = (2 * P) -  prev_low 
    S1 = (2 * P) -  prev_high 

    R2 = P + ( prev_high  -  prev_low )
    S2 = P - ( prev_high  -  prev_low )

    R3 =  prev_high  + 2 * (P -  prev_low )
    S3 =  prev_low  - 2 * ( prev_high  - P)

    R4 =  prev_high  + 3 * (P -  prev_low )   
    S4 =  prev_low  - 3 * ( prev_high  - P)   

    df['P']  = P
    df['BC']  = BC
    df['TC']  = TC
    df['R1']  = R1
    df['R2']  = R2
    df['R3']  = R3
    df['R4']  = R4
    df['S1']  = S1
    df['S2']  = S2
    df['S3']  = S3
    df['S4']  = S4

    return df.round(2)

#  Adding technical parameters
def add_cpr_points(df_sample):
    df_sample['date']  = df_sample['timestamp'].dt.date
    cpr_data = []
    grouped = df_sample.groupby('date')
    prev_day = None
    for current_day, group in grouped:
        # print(group)
        
        if prev_day is not None:
            high = prev_day['high'] .max()
            low = prev_day['low'] .min()
            close = prev_day['close'] .iloc[-1]
            group = apply_pivot_levels(group, high, low, close)
            # print(pd.DataFrame(group.tail(20)))
            for i, row in group.iterrows():
                cpr_data.append({
                    'timestamp': row['timestamp'] ,
                    'date' : current_day,
                    'open': row['open'] ,
                    'high': row['high'] ,
                    'low': row['low'],
                    'close': row['close'] ,
                    'volume' : row['volume'],
                    'pivot': row['P'],
                    'tc': row['TC'],
                    'bc': row['BC'],
                    'R1'  : row['R1'],
                    'R2'  : row['R2'],
                    'R3'  : row['R3'],
                    'R4'  : row['R4'],
                    'S1'  : row['S1'],
                    'S2'  : row['S2'],
                    'S3'  : row['S3'],
                    'S4'  : row['S4']       
                })
        prev_day = group
    # print(cpr_data)

    cpr_df = pd.DataFrame(cpr_data)
    
    # Strategy: Breakout above TC
    if cpr_df.empty:
        return cpr_df
    
    cpr_df['direction'] = np.where(cpr_df['close'] > cpr_df['open'], 'Green', 'Red')

    cpr_df.loc[cpr_df['direction'] == 'Green','signal'] = (
        (cpr_df['close'] > cpr_df['tc']) & (cpr_df['close'].shift(1) < cpr_df['tc'])
    )
    cpr_df.loc[cpr_df['direction'] == 'Red','signal'] = (
        (cpr_df['close'] < cpr_df['bc']) & (cpr_df['close'].shift(1) > cpr_df['bc'])
    )
    return cpr_df

    # Technical Parameters
def compute_rsi(df, period=14):
    delta = df['close'].diff()

    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()

    rs = avg_gain / avg_loss
    rsi = round(100 - (100 / (1 + rs)), 2)

    return rsi

def add_technical_parameters(cpr_df):
    if cpr_df.empty:
        return cpr_df
    # Price Change in %
    cpr_df['price_change_pct'] = round((cpr_df['close'] - cpr_df['open'])/cpr_df['open']*100,2)
    
    # Trend of signal
    cpr_df['trend'] = np.where(cpr_df["direction"] == "Green", "Bullish", "Bearish")
    
    # EMA (above/below price)
    cpr_df['ema_20'] = cpr_df['close'].ewm(span=20).mean()
    cpr_df['ema_50'] = cpr_df['close'].ewm(span=50).mean()
    
    # Simple Moving Average (SMA)
    days = 5
    cpr_df['sma'] = cpr_df['close'].rolling(days).mean()
    
    # RSI (0-100)(Overbought/Oversold)
    cpr_df['rsi'] = compute_rsi(cpr_df)
    # Signal for rsi 
    # buy when the 14-day RSI is lower than 30 and the closing price is greater than the 5-day SMA
    # sell when the 14-day RSI is greater than 70 and the closing price is lower than the 5-day SMA
    cpr_df[['ema_20', 'ema_50', 'sma', 'rsi']] = round(cpr_df[['ema_20', 'ema_50', 'sma', 'rsi']], 2)
    return cpr_df

