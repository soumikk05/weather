import pandas as pd
import numpy as np
from typing import Tuple

def get_time_blocked_splits(df: pd.DataFrame, time_col: str = "init_time") -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Creates strict chronological time-blocked splits:
    - Train: First 70% of the timeline
    - Val: Next 15% of the timeline
    - Test: Final 15% of the timeline
    
    This groups forecasts from the same event together and ensures no future information 
    leaks into the training of past events.
    """
    if time_col not in df.columns:
        # Fallback if the column is just date or index
        df = df.sort_values("date") if "date" in df.columns else df.sort_index()
    else:
        # Ensure it's sorted by time
        df[time_col] = pd.to_datetime(df[time_col])
        df = df.sort_values(time_col)
        
    n = len(df)
    train_end = int(n * 0.70)
    val_end = int(n * 0.85)
    
    # We should ensure that if there are multiple rows for the same date (e.g. different locations),
    # they don't get split across sets.
    # Find the date at train_end and val_end
    if "date" in df.columns:
        train_date_cutoff = df.iloc[train_end]["date"]
        val_date_cutoff = df.iloc[val_end]["date"]
        
        train_df = df[df["date"] < train_date_cutoff].copy()
        val_df = df[(df["date"] >= train_date_cutoff) & (df["date"] < val_date_cutoff)].copy()
        test_df = df[df["date"] >= val_date_cutoff].copy()
    else:
        train_df = df.iloc[:train_end].copy()
        val_df = df.iloc[train_end:val_end].copy()
        test_df = df.iloc[val_end:].copy()
        
    return train_df, val_df, test_df
