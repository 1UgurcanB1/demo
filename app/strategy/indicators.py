import numpy as np
import pandas as pd

def indicators(df: pd.DataFrame) -> pd.DataFrame:
    d=df.copy(); c=d.close; delta=c.diff()
    for n in [9,20,50,200]: d[f'ema{n}']=c.ewm(span=n,adjust=False).mean()
    gain=delta.clip(lower=0).ewm(alpha=1/14,adjust=False).mean()
    loss=(-delta.clip(upper=0)).ewm(alpha=1/14,adjust=False).mean()
    d['rsi']=100-100/(1+gain/loss.replace(0,np.nan)); d['rsi']=d.rsi.where(loss!=0,100).where((gain!=0)|(loss!=0),50).fillna(50)
    d['macd']=c.ewm(span=12,adjust=False).mean()-c.ewm(span=26,adjust=False).mean()
    d['macd_signal']=d.macd.ewm(span=9,adjust=False).mean()
    d['roc']=c.pct_change(10)*100
    tr=pd.concat([d.high-d.low,(d.high-c.shift()).abs(),(d.low-c.shift()).abs()],axis=1).max(axis=1)
    d['atr']=tr.ewm(alpha=1/14,adjust=False).mean()
    up=d.high.diff(); down=-d.low.diff()
    plus=up.where((up>down)&(up>0),0).ewm(alpha=1/14,adjust=False).mean()/d.atr*100
    minus=down.where((down>up)&(down>0),0).ewm(alpha=1/14,adjust=False).mean()/d.atr*100
    d['adx']=(100*(plus-minus).abs()/(plus+minus).replace(0,np.nan)).ewm(alpha=1/14,adjust=False).mean().fillna(0)
    d['bb_mid']=c.rolling(20).mean(); std=c.rolling(20).std()
    d['bb_upper']=d.bb_mid+2*std; d['bb_lower']=d.bb_mid-2*std
    d['avg_volume']=d.volume.shift(1).rolling(20).mean(); d['rvol']=d.volume/d.avg_volume
    d['support']=d.low.shift(1).rolling(20).min(); d['resistance']=d.high.shift(1).rolling(20).max()
    return d.replace([np.inf,-np.inf],np.nan).fillna(0)
