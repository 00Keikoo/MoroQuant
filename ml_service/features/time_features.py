"""Time-based features for ML trading system."""

import pandas as pd
import numpy as np
from datetime import datetime


def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add time-based features from timestamp.

    Args:
        df: DataFrame with timestamp column (milliseconds)

    Returns:
        DataFrame with time features added
    """
    df = df.copy()

    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)

    df['hour_of_day'] = df['datetime'].dt.hour
    df['day_of_week'] = df['datetime'].dt.dayofweek

    df['is_asia_session'] = ((df['hour_of_day'] >= 0) & (df['hour_of_day'] <= 8)).astype(int)
    df['is_london_session'] = ((df['hour_of_day'] >= 7) & (df['hour_of_day'] <= 16)).astype(int)
    df['is_ny_session'] = ((df['hour_of_day'] >= 12) & (df['hour_of_day'] <= 21)).astype(int)

    df['session_overlap'] = ((df['hour_of_day'] >= 12) & (df['hour_of_day'] <= 16)).astype(int)

    days_in_month = df['datetime'].dt.days_in_month
    day_of_month = df['datetime'].dt.day
    df['days_to_month_end'] = days_in_month - day_of_month

    df['is_month_end_week'] = (df['days_to_month_end'] <= 7).astype(int)

    df['is_monday'] = (df['day_of_week'] == 0).astype(int)
    df['is_friday'] = (df['day_of_week'] == 4).astype(int)

    df = df.drop(columns=['datetime'], errors='ignore')

    return df
