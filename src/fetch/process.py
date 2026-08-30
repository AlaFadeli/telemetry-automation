import pandas as pd
import numpy as np






def resample_telemetry(df):
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date')
    df = df.set_index('Date')
    df = df.drop(columns=['Time'])
    continuous = df[['Speed','RPM','X','Y','Throttle','Brake']]
    discrete = df[['nGear','DRS']]
    continuous = continuous.infer_objects() 
    continuous = continuous.resample('100ms').interpolate()
    discrete = discrete.resample('100ms').ffill()
    df = pd.concat([continuous,discrete], axis=1)


    df['SessionTime'] = np.arange(len(df)) * 0.1
    return df 
    
