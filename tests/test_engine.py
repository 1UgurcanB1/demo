import pytest
import numpy as np
from app.config import Settings
from app.risk.manager import quantity,pause_reason
from app.trading.paper_broker import PaperBroker
from app.data.mock import MockDataProvider
from app.strategy.indicators import indicators
from app.strategy.scoring import score
from app.data.base import validate_candles
from app.backtest.engine import run_backtest

def signal():return {'symbol':'ASELS','entry':100.,'price':100.,'stop':95.,'target1':110.,'target2':120.,'eligible':True}

def test_cash_and_realized_pnl_reconcile():
    b=PaperBroker(Settings());b.buy(signal(),'2025-01-01');p=b.positions[0];b.sell(p,110,'2025-01-02','MANUAL DEMO EXIT')
    assert b.cash==pytest.approx(b.initial+sum(t['net'] for t in b.trades))
    assert b.trades[0]['commission']>0
    assert not b.positions

def test_risk_size_includes_cost_and_caps():
    c=Settings();q=quantity(100000,100000,100,95,c)
    assert q*100*(1+c.slippage)*(1+c.commission)<=10000
    assert quantity(100000,0,100,95,c)==0
    assert pause_reason(89000,100000,95000,c)=='MAX DRAWDOWN WARNING'

def test_stop_wins_ambiguous_bar_and_gap_fill():
    b=PaperBroker(Settings());b.buy(signal(),'one');b.mark({'ASELS':{'open':90,'high':130,'low':89,'close':110,'atr':3}},'two')
    assert len(b.trades)==1 and b.trades[0]['reason']=='STOP LOSS'
    assert b.trades[0]['sell_price']<90

def test_partial_profit_no_oversell():
    b=PaperBroker(Settings());b.buy(signal(),'one');q=b.positions[0]['quantity']
    b.mark({'ASELS':{'open':100,'high':121,'low':99,'close':120,'atr':3}},'two')
    assert sum(t['quantity'] for t in b.trades)+sum(p['quantity'] for p in b.positions)==q
    assert b.positions[0]['stage']==2 and b.positions[0]['trailing']
    assert b.cash>=0

def test_future_candles_do_not_change_past_signal():
    p=MockDataProvider();f=p.get_historical_data('ASELS');past=f.iloc[:500]
    a=score('ASELS',indicators(f).iloc[:500],'BULLISH',Settings())
    f.iloc[500:,f.columns.get_loc('close')]*=10
    b=score('ASELS',indicators(f).iloc[:500],'BULLISH',Settings())
    assert a==b
    validate_candles(past,past.index[-1])
    with pytest.raises(ValueError):validate_candles(past,past.index[-1]+__import__('pandas').Timedelta(days=1))

def test_small_backtest_reconciles():
    p=MockDataProvider();r=run_backtest(p,'2025-01-01','2025-02-01',Settings(min_score=30,min_expected=10),['ASELS','THYAO'])
    assert r['metrics']['final']==pytest.approx(100000+sum(t['net'] for t in r['trades']))
    assert all(t['buy_time']<=t['sell_time'] for t in r['trades'])

def test_invalid_settings_rejected():
    with pytest.raises(ValueError):Settings(partial_1=.7,partial_2=.7)
    with pytest.raises(ValueError):Settings(weights={'trend':100})
