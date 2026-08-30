import pandas as pd
import numpy as np






def resample_telemetry(df):
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date')
    df = df.set_index('Date')
    df = df.drop(columns=['Time'])                   
    df = df.resample('100ms').interpolate()         
    df['nGear'] = df['nGear'].ffill()
    df['DRS']   = df['DRS'].ffill()
    df['SessionTime'] = np.arange(len(df)) * 0.1
    return df
