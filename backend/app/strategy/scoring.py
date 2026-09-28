import numpy as np
from app.strategy.indicators import indicators
from app.config import Settings

def regime(frame):
    r=indicators(frame).iloc[-1]
    return 'BULLISH' if r.close>r.ema50>r.ema200 and r.roc>0 else 'BEARISH' if r.close<r.ema200 and r.roc<0 else 'NEUTRAL'

def score(symbol, frame, market, cfg: Settings):
    d=frame if "ema200" in frame.columns else indicators(frame); r=d.iloc[-1]; price=float(r.close)
    fast=float(d.close.ewm(span=cfg.ema_fast,adjust=False).mean().iloc[-1]); slow=float(d.close.ewm(span=cfg.ema_slow,adjust=False).mean().iloc[-1])
    trend=price>fast>slow>r.ema200
    momentum=r.macd>r.macd_signal and cfg.rsi_min<r.rsi<cfg.rsi_max and r.roc>0
    breakout=price>r.resistance; pullback=abs(price-fast)<r.atr and price>slow
    risk=max(float(r.atr)*cfg.atr_multiplier,price*.01); stop=max(.01,price-risk)
    target1=price+cfg.target_rr1*risk; target2=price+cfg.target_rr2*risk
    costs=2*price*(cfg.commission+cfg.slippage); rr=(target2-price-costs)/(price-stop+costs)
    parts={'trend':100 if trend else 35 if price>slow else 0,'momentum':100 if momentum else 30,'volume':min(100,float(r.rvol)*60),'action':100 if breakout else 75 if pullback else 25,'rr':min(100,rr/4*100),'market':100 if market=='BULLISH' else 50 if market=='NEUTRAL' else 0}
    opportunity=sum(parts[k]*cfg.weights[k]/100 for k in parts)
    # Historical 10-bar outcomes are included only if their full horizon already elapsed.
    similar=(d.rsi.between(float(r.rsi)-8,float(r.rsi)+8)) & ((d.close>d.ema50)==(price>r.ema50))
    outcomes=(d.close.shift(-10)/d.close-1-2*(cfg.commission+cfg.slippage))[similar].dropna()
    probability=float((outcomes>0).mean()) if len(outcomes)>=20 else .5
    expectancy=probability*rr-(1-probability)
    expected=float(np.clip(.45*opportunity+25*min(2,max(-1,expectancy))+10*min(1,r.adx/30),0,100))
    reasons=[]
    for ok,msg in [(trend,'EMA trendi uygun değil'),(momentum,'Momentum teyidi eksik'),(r.rvol>=1,'Hacim teyidi eksik'),(market!='BEARISH','Piyasa düşüş rejiminde'),(rr>=cfg.min_rr,'Risk/getiri düşük'),(price-fast<2*r.atr,'Fiyat aşırı uzamış'),(breakout or r.resistance-price>risk,'Yakın direnç'),(opportunity>=cfg.min_score,'Fırsat skoru düşük'),(expected>=cfg.min_expected,'Beklenti skoru düşük')]:
        if not ok: reasons.append(msg)
    return {'symbol':symbol,'price':price,'score':round(opportunity,1),'expected':round(expected,1),'entry':price,'stop':stop,'target1':target1,'target2':target2,'rr':round(rr,2),'potential':(target2/price-1)*100,'risk_pct':(1-stop/price)*100,'trend':'UP' if trend else 'MIXED','market':market,'rsi':float(r.rsi),'rvol':float(r.rvol),'atr':float(r.atr),'adx':float(r.adx),'probability':probability,'samples':len(outcomes),'expectancy':expectancy,'parts':parts,'eligible':not reasons,'reasons':reasons,'signal':'STRONG BUY CANDIDATE' if opportunity>=80 else 'BUY CANDIDATE' if opportunity>=70 else 'WATCHLIST' if opportunity>=60 else 'NO TRADE'}
