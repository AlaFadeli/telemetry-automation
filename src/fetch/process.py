import pandas as pd
import numpy as np
from pathlib import Path





def resample_telemetry(df):
    driver = df['Driver'].iloc[0]
    lapno = df['LapNumber'].iloc[0]
    laptime = df['LapTime'].iloc[0]
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date')
    df = df.set_index('Date')
    df = df.drop(columns=['Time', 'Driver', 'LapNumber', 'LapTime', 'Source', 'SessionTime'])
    df = df.infer_objects()
    df = df.resample('100ms').mean(numeric_only=True)
    df = df.interpolate()
    df['nGear'] = df['nGear'].ffill()
    df['DRS']   = df['DRS'].ffill()
    df['Driver'] = driver
    df['LapNumber'] = lapno
    df['LapTime'] = laptime
    df['SessionTime'] = np.arange(len(df)) * 0.1
    return df


def run_processing(raw_dir, out_dir):
    df = pd.read_csv(Path(raw_dir) / 'telemetry.csv')
    resampled = [resample_telemetry(group) for key, group in df.groupby(['Driver', 'LapNumber'])]
    processed = pd.concat(resampled, ignore_index=True)
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    processed.to_parquet(Path(out_dir) / 'telemetry.parquet')
