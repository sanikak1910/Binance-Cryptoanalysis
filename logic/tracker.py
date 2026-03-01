import pandas as pd
from functools import reduce
from logic.backtest import analyze_r1_hit_targets

def track_last_hit_and_profits(cpr_df):

    target_levels = {
        "Green": ['R1', 'R2', 'R3', 'R4', 'SL', 'None'],
        "Red": ['S1', 'S2', 'S3', 'S4', 'SL', 'None'] 
    }

    all_results = []

    for direction, targets in target_levels.items():
        # To collect per-target results
        target_data = {}

        for target in targets:
            df = analyze_r1_hit_targets(cpr_df, direction=direction, target=target).copy()

            # Rename generic columns to be target-specific
            df.rename(columns={
                'hit': f"hit_{target}",
                'profit': f"profit_{target}",
                'hit_timestamp': f"hit_timestamp_{target}"
            }, inplace=True)

            df['direction'] = direction
            target_data[target] = df
            
        
        # Merge all R/S levels together for the direction
        merged_df = reduce(
            lambda left, right: pd.merge(
                left, right, on=['date', 'entry_timestamp', 'direction'], how='outer'
            ),
            target_data.values()
        )
        # Determine last hit and fallback
        last_hits = []
        last_hit_timestamps = []
        
        for idx, row in merged_df.iterrows():
            hits = []
            sl_hit = None
            for target in targets:
                hit_val = row.get(f"hit_{target}")
                ts_val = row.get(f"hit_timestamp_{target}")
                if pd.notna(hit_val) and hit_val == target:
                    hits.append((target, ts_val))
                    
            if hits:
                last_hit, hit_time = hits[-1]
            else:
                last_hit, hit_time = 'None', None

            last_hits.append(last_hit)
            last_hit_timestamps.append(hit_time)

        merged_df['final_hit'] = last_hits
        merged_df['hit_timestamp_final'] = last_hit_timestamps

        # Optional: Add fallback price if no target hit
        merged_df['fallback_price'] = merged_df['close'] if 'close' in merged_df else None
        merged_df['used_fallback'] = merged_df['final_hit'] == 'None'

        # Nullify profits after final hit
        progressive_targets = ['R1','R2','R3','R4','S1','S2','S3','S4']
        for _, row in merged_df.iterrows():
            final_hit = row['final_hit']
            if final_hit in progressive_targets:
                idx = progressive_targets.index(final_hit)
                valid_targets = progressive_targets[:idx + 1]
            else:
                valid_targets = []
                
            for target in targets:
                if target in progressive_targets and target not in valid_targets:
                    row[f'profit_{target}'] = None

            # Replace the updated row
            merged_df.loc[row.name] = row
        all_results.append(merged_df)
    final_df = pd.concat(all_results, ignore_index=True)
    final_df = final_df.sort_values(by=['date', 'direction']).reset_index(drop=True)
    final_df['final_hit_profit'] = final_df.apply(
    lambda row: row[f"profit_{row['final_hit']}"] if f"profit_{row['final_hit']}" in row else None,
    axis=1
    )
    return final_df