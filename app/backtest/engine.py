from app.config import Settings
from app.strategy.indicators import indicators
from app.strategy.scoring import score
from app.trading.paper_broker import PaperBroker


def run_backtest(provider,start,end,cfg: Settings,symbols=None):
    symbols=symbols or provider.get_bist100_symbols()
    frames={s:indicators(provider.get_historical_data(s)) for s in symbols}
    index=indicators(provider.get_index_data())
    import pandas as pd
    if pd.Timestamp(start)<index.index[0] or pd.Timestamp(end)>index.index[-1]:raise ValueError('Tarih aralığı mevcut sentetik verinin dışında')
    selected=index.loc[start:end]
    if len(selected)<5:raise ValueError('En az 5 seans içeren tarih aralığı seçin')
    if index.index.get_loc(selected.index[0])<210:raise ValueError('İndikatörler için 210 seans ön veri gerekli')
    broker=PaperBroker(cfg); pending=[]
    broker.record(str(selected.index[0].date())+' başlangıç')
    for date,idx in selected.iterrows():
        stamp=str(date.date()); bars={s:d.loc[date].to_dict() for s,d in frames.items()}
        # Previous close creates order; this session open executes it, without future high/low.
        broker.day_start=broker.equity()
        for signal in pending:
            original=signal['entry']; opening=bars[signal['symbol']]['open']
            if opening<=signal['stop'] or abs(opening/original-1)>.03:continue
            shifted={**signal,'entry':opening,'price':opening}
            cost=2*opening*(cfg.commission+cfg.slippage)
            if (signal['target2']-opening-cost)/(opening-signal['stop']+cost)<cfg.min_rr:continue
            try:broker.buy(shifted,stamp)
            except ValueError:continue
        broker.mark(bars,stamp,reset_day=False); broker.record(stamp)
        market='BULLISH' if idx.close>idx.ema50>idx.ema200 and idx.roc>0 else 'BEARISH' if idx.close<idx.ema200 and idx.roc<0 else 'NEUTRAL'
        signals=[score(s,d.loc[:date],market,cfg) for s,d in frames.items()]
        pending=sorted([s for s in signals if s['eligible']],key=lambda s:s['expected'],reverse=True)
    for p in broker.positions.copy():broker.sell(p,p['current'],str(selected.index[-1].date()),'BACKTEST END')
    broker.record(str(selected.index[-1].date())+' kapanış')
    return {'metrics':broker.summary(),'curve':broker.curve,'trades':broker.trades,'data_label':'DEMO DATA','symbols':len(symbols),'execution':'Önceki kapanış sinyali → sonraki seans açılışı. Son gün tasfiye edilir.'}
