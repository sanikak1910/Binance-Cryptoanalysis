import pandas as pd
from functools import reduce
import streamlit as st
import numpy as np

def generate_signals(df):
    df = df.copy()
    df["ema_trend"] = np.where(df["ema_20"]>df["ema_50"],1,-1)

    df["rsi_regime"] = 0
    df.loc[df["rsi"] < 30, "rsi_regime"] = 1
    df.loc[df["rsi"] > 70, "rsi_regime"] = -1
    # CPR breakout
    df["score"] = (
        df["ema_trend"]+df["rsi_regime"]+df["signal"]
    )
    df["final_signal"] = "WAIT"
    df.loc[df["score"] >= 2, "final_signal"] = "BUY"
    df.loc[df["score"] <= -2, "final_signal"] = "SELL"
    
    return df
# cpr_df = pd.read_csv("Technical_parameter_data.csv")
# cpr_df['timestamp'] = pd.to_datetime(cpr_df["timestamp"])
# cpr_df['date'] = pd.to_datetime(cpr_df['date']).dt.date

# def analyze_r1_hit_targets(direction, target):
#     results = []
#     capital = 500
#     for day in cpr_df['date'].unique():
#         filtered_df = cpr_df[cpr_df['date'] == day]
#         # print(filtered_df)
#         if direction not in ['Green', 'Red']:
#             raise ValueError("Invalid direction. Use 'Green' or 'Red'.")

#         signal_filter = filtered_df[(filtered_df['signal'] == 1) & (filtered_df['direction'] == direction)]

#         if signal_filter.empty:
#             continue

#         first_candle = signal_filter.iloc[0]

#         entry_ts = first_candle['timestamp']
#         entry_price = first_candle['high'] if direction == 'Green' else first_candle['low']
#         stop_loss = round(first_candle['tc'] - (first_candle['tc'] * 0.005), 2) if direction == 'Green' else round(first_candle['bc'] + (first_candle['bc'] * 0.005), 2)

#         try:
#             target_value = first_candle[target]
#         except KeyError:
#             target_value = None  # Handle cases like target='None'

#         quantity = capital / entry_price

#         # Only check candles from entry time onward, and matching direction
#         filtered_df = filtered_df[(filtered_df['timestamp'] >= entry_ts) & (filtered_df['direction'] == direction)]

#         hit = None
#         hit_timestamp = None
#         sell_price = None

#         for _, row in filtered_df.iterrows():
#             if direction == 'Green':
#                 if target_value is not None and row['close'] >= target_value and row['open'] < target_value:
#                     hit = target
#                     sell_price = row['close']
#                     hit_timestamp = row['timestamp']
#                     break
#                 elif row['low'] <= stop_loss:
#                     hit = 'SL'
#                     sell_price = stop_loss
#                     hit_timestamp = row['timestamp']
#                     break
#             else:
#                 if target_value is not None and row['close'] <= target_value and row['open'] > target_value:
#                     hit = target
#                     sell_price = row['close']
#                     hit_timestamp = row['timestamp']
#                     break
#                 elif row['high'] >= stop_loss:
#                     hit = 'SL'
#                     sell_price = stop_loss
#                     hit_timestamp = row['timestamp']
#                     break

#         # If neither target nor SL hit, exit at last candle's close
#         if hit == None:
#             last_row = filtered_df.iloc[-1]
#             sell_price = last_row['close']

#         # Calculate profit
#         if direction == 'Green':
#             profit = round((sell_price - entry_price) * quantity, 2)
#         else:
#             profit = round((entry_price - sell_price) * quantity, 2)

#         results.append({
#             'date': day,
#             'entry_timestamp': entry_ts,
#             'direction': direction,
#             'hit': hit,
#             'profit': profit,
#             'hit_timestamp': hit_timestamp
#         })
#     result_df = pd.DataFrame(results)
#     return result_df

# def track_last_hit_and_profits(analyze_hit_fn):
#     target_levels = {
#         "Green": ['R1', 'R2', 'R3', 'R4', 'SL', 'None'],
#         "Red": ['S1', 'S2', 'S3', 'S4', 'SL', 'None'] 
#     }

#     all_results = []

#     for direction, targets in target_levels.items():
#         # To collect per-target results
#         target_data = {}

#         for target in targets:
#             df = analyze_hit_fn(direction=direction, target=target).copy()

#             # Rename generic columns to be target-specific
#             df.rename(columns={
#                 'hit': f"hit_{target}",
#                 'profit': f"profit_{target}",
#                 'hit_timestamp': f"hit_timestamp_{target}"
#             }, inplace=True)

#             df['direction'] = direction
#             target_data[target] = df
            
        
#         # Merge all R/S levels together for the direction
#         merged_df = reduce(
#             lambda left, right: pd.merge(
#                 left, right, on=['date', 'entry_timestamp', 'direction'], how='outer'
#             ),
#             target_data.values()
#         )
#         # Determine last hit and fallback
#         last_hits = []
#         last_hit_timestamps = []
        
#         for idx, row in merged_df.iterrows():
#             hits = []
#             sl_hit = None
#             for target in targets:
#                 hit_val = row.get(f"hit_{target}")
#                 ts_val = row.get(f"hit_timestamp_{target}")
#                 if pd.notna(hit_val) and hit_val == target:
#                     hits.append((target, ts_val))
                    
#             if hits:
#                 last_hit, hit_time = hits[-1]
#             else:
#                 last_hit, hit_time = 'None', None

#             last_hits.append(last_hit)
#             last_hit_timestamps.append(hit_time)

#         merged_df['final_hit'] = last_hits
#         merged_df['hit_timestamp_final'] = last_hit_timestamps

#         # Optional: Add fallback price if no target hit
#         merged_df['fallback_price'] = merged_df['close'] if 'close' in merged_df else None
#         merged_df['used_fallback'] = merged_df['final_hit'] == 'None'

#         # Nullify profits after final hit
#         progressive_targets = ['R1','R2','R3','R4','S1','S2','S3','S4']
#         for _, row in merged_df.iterrows():
#             final_hit = row['final_hit']
#             if final_hit in progressive_targets:
#                 idx = progressive_targets.index(final_hit)
#                 valid_targets = progressive_targets[:idx + 1]
#             else:
#                 valid_targets = []
                
#             for target in targets:
#                 if target in progressive_targets and target not in valid_targets:
#                     row[f'profit_{target}'] = None

#             # Replace the updated row
#             merged_df.loc[row.name] = row
#         all_results.append(merged_df)
#     final_df = pd.concat(all_results, ignore_index=True)
#     final_df = final_df.sort_values(by=['date', 'direction']).reset_index(drop=True)
#     final_df['final_hit_profit'] = final_df.apply(
#     lambda row: row[f"profit_{row['final_hit']}"] if f"profit_{row['final_hit']}" in row else None,
#     axis=1
#     )
#     return final_df


# # You must define `analyze_r1_hit_targets` to match the requiRed format
# # It should return a DataFrame with at least:
# # ['date', 'entry_timestamp', 'hit', 'profit', 'hit_timestamp']

# # print(cpr_df.dtypes)
# final_df = track_last_hit_and_profits(analyze_hit_fn=analyze_r1_hit_targets)
# # final_df['date'] = pd.to_datetime(final_df['date'])  # Convert to datetime if not already


# final_df = track_last_hit_and_profits(technical_df)
# final_df = final_df.sort_values(by=['date', 'direction']).reset_index(drop=True)
# final_df['final_hit_profit'] = final_df.apply(
#     lambda row: row[f"profit_{row['final_hit']}"] if f"profit_{row['final_hit']}" in row else None,
#     axis=1
#     )
# st.subheader("Backtest Results")
# st.dataframe(final_df[["date", "entry_timestamp","direction","final_hit_profit","final_hit"]])

