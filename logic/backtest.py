import pandas as pd
from functools import reduce

def analyze_r1_hit_targets(cpr_df, direction, target):
    results = []
    capital = 500

    for day in cpr_df['date'].unique():

        filtered_df = cpr_df[cpr_df['date'] == day]

        signal_filter = filtered_df[
            (filtered_df['signal'] == 1) &
            (filtered_df['direction'] == direction)
        ]

        if signal_filter.empty:
            continue

        first_candle = signal_filter.iloc[0]

        entry_ts = first_candle['timestamp']
        entry_price = (
            first_candle['high']
            if direction == 'Green'
            else first_candle['low']
        )

        stop_loss = (
            round(first_candle['tc'] * 0.995, 2)
            if direction == 'Green'
            else round(first_candle['bc'] * 1.005, 2)
        )

        target_value = first_candle.get(target)

        quantity = capital / entry_price

        filtered_df = filtered_df[
            (filtered_df['timestamp'] >= entry_ts) &
            (filtered_df['direction'] == direction)
        ]

        hit = None
        hit_timestamp = None
        sell_price = None

        for _, row in filtered_df.iterrows():

            if direction == 'Green':

                if target_value and row['close'] >= target_value:
                    hit = target
                    sell_price = row['close']
                    hit_timestamp = row['timestamp']
                    break

                elif row['low'] <= stop_loss:
                    hit = 'SL'
                    sell_price = stop_loss
                    hit_timestamp = row['timestamp']
                    break

            else:

                if target_value and row['close'] <= target_value:
                    hit = target
                    sell_price = row['close']
                    hit_timestamp = row['timestamp']
                    break

                elif row['high'] >= stop_loss:
                    hit = 'SL'
                    sell_price = stop_loss
                    hit_timestamp = row['timestamp']
                    break

        if hit is None:
            sell_price = filtered_df.iloc[-1]['close']

        profit = (
            (sell_price - entry_price) * quantity
            if direction == 'Green'
            else (entry_price - sell_price) * quantity
        )

        results.append({
            "date": day,
            "entry_timestamp": entry_ts,
            "direction": direction,
            "hit": hit,
            "profit": round(profit, 2),
            "hit_timestamp": hit_timestamp
        })

    return pd.DataFrame(results)
