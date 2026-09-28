import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime,timezone
from threading import RLock
from typing import Literal
import pandas as pd
from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI,HTTPException,WebSocket,WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel,Field,model_validator
from starlette.concurrency import run_in_threadpool
from app.config import Settings
from app.data.mock import MockDataProvider
from app.data.base import validate_candles
from app.database.store import load,save_all
from app.strategy.indicators import indicators
from app.strategy.scoring import score,regime
from app.trading.paper_broker import PaperBroker
from app.backtest.engine import run_backtest
from app.backtest.optimizer import optimize

logging.basicConfig(level=logging.INFO); logger=logging.getLogger('paper')
lock=RLock(); provider=MockDataProvider(); cfg=Settings(**(load('settings') or [{}])[0]); broker=PaperBroker(cfg)
state=load('portfolio')
if state:
    st=state[0]; provider.cursor=st.pop('cursor',650)
    for k,v in st.items():setattr(broker,k,v)
    broker.auto=False # Require explicit resume after server restart.
    broker.positions=load('positions');broker.trades=load('trades');broker.orders=load('orders');broker.curve=load('performance')
else:broker.record(str(provider.get_index_data().index[-1].date()))
opportunities=[]; market='NEUTRAL'; last_scan=None; warning=None; backtests=load('backtests')

def persist():
    st={k:getattr(broker,k) for k in ['cash','initial','peak','day_start','paused','auto','notifications']};st['cursor']=provider.cursor
    save_all({'portfolio':[st],'positions':broker.positions,'trades':broker.trades,'orders':broker.orders,'performance':broker.curve,'settings':[cfg.model_dump()],'signals':opportunities,'market_snapshots':[{'market':market,'last_scan':last_scan,'cursor':provider.cursor}],'backtests':backtests[-20:]})

def scan(advance=False):
    global opportunities,market,last_scan,warning
    with lock:
        if advance:provider.advance()
        market=regime(provider.get_index_data());expected=provider.get_index_data().index[-1];warning=None
        try:
            frames=provider.get_market_data()
            for d in frames.values():validate_candles(d,expected,provider.get_index_data().index)
            opportunities=sorted([score(s,d,market,cfg) for s,d in frames.items()],key=lambda s:s['expected'],reverse=True)
            if advance:
                broker.mark({s:indicators(d).iloc[-1].to_dict() for s,d in frames.items()},str(expected.date()))
            if broker.auto and advance:
                for signal in opportunities:
                    if signal['eligible']:
                        try:broker.buy(signal,str(expected.date()))
                        except ValueError:continue
            if advance:broker.record(str(expected.date()))
            eligible=[s for s in opportunities if s['eligible']]
            if eligible:broker.notify('NEW OPPORTUNITY',f"{eligible[0]['symbol']} · skor {eligible[0]['score']}")
        except ValueError as exc:
            warning=str(exc);opportunities=[];broker.notify('DATA WARNING',warning)
        last_scan=datetime.now(timezone.utc).isoformat();persist()

async def loop():
    while True:
        await asyncio.sleep(cfg.scanner_interval)
        try:await run_in_threadpool(scan,True)
        except Exception:logger.exception('Scanner failed')

@asynccontextmanager
async def lifespan(app):
    await run_in_threadpool(scan);task=asyncio.create_task(loop())
    yield
    task.cancel()
    try:await task
    except asyncio.CancelledError:pass

app=FastAPI(title='BIST 100 Paper Trading',lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=['http://localhost:3000','http://127.0.0.1:3000'],allow_methods=['GET','POST','PUT'],allow_headers=['Content-Type'])

class Buy(BaseModel):symbol:str=Field(min_length=2,max_length=15)
class Reset(BaseModel):initial_balance:float=Field(100000,ge=1000,le=1e9)
class BacktestRequest(BaseModel):
    start:str='2025-01-01'
    end:str='2025-06-27'
    initial_balance:float=Field(100000,ge=1000,le=1e9)
    risk_per_trade:float=Field(.01,gt=0,le=.05)
    min_score:float=Field(70,ge=0,le=100)
    min_rr:float=Field(2,ge=1,le=10)
    @model_validator(mode='after')
    def dates(self):
        try:a=pd.Timestamp(self.start);b=pd.Timestamp(self.end)
        except Exception:raise ValueError('Tarih geçersiz')
        if a>b:raise ValueError('Tarih sıralaması geçersiz')
        return self

class OptimizationRequest(BacktestRequest):
    grid:dict[str,list[float]]=Field(default_factory=lambda:{'min_score':[65,75],'atr_multiplier':[1.5,2.5]})

def dashboard():
    return {**broker.summary(),'market':market,'last_scan':last_scan,'scanner_interval':cfg.scanner_interval,'data_warning':warning,'data_label':'DEMO DATA','simulation_date':str(provider.get_index_data().index[-1].date()),'universe_count':len(provider.get_bist100_symbols()),'opportunity_count':sum(s['eligible'] for s in opportunities)}

@app.get('/api/dashboard')
def get_dashboard():
    with lock:return dashboard()
@app.get('/api/stocks')
@app.get('/api/opportunities')
def stocks():
    with lock:return opportunities
@app.get('/api/stocks/{symbol}')
def stock(symbol:str):
    with lock:
        if symbol not in provider.get_bist100_symbols():raise HTTPException(404,'Sembol bulunamadı')
        d=indicators(provider.get_historical_data(symbol)).tail(100);d.index=d.index.strftime('%Y-%m-%d')
        return {'signal':next((s for s in opportunities if s['symbol']==symbol),None),'candles':d.reset_index(names='date').to_dict('records')}
@app.get('/api/positions')
def positions():
    with lock:return [dict(p,unrealized=(p['current']-p['entry'])*p['quantity']-p['entry_fee_per_share']*p['quantity']) for p in broker.positions]
@app.get('/api/trades')
def trades():
    with lock:return broker.trades
@app.get('/api/performance')
def performance():
    with lock:return {'metrics':broker.summary(),'curve':broker.curve}
@app.post('/api/paper/buy')
def buy(req:Buy):
    with lock:
        if warning:raise HTTPException(409,'DATA WARNING')
        signal=next((s for s in opportunities if s['symbol']==req.symbol),None)
        if not signal:raise HTTPException(404,'Sembol bulunamadı')
        try:broker.buy(signal,str(provider.get_index_data().index[-1].date()),manual=True)
        except ValueError as exc:raise HTTPException(409,str(exc))
        persist();return dashboard()
@app.post('/api/paper/sell')
def sell(req:Buy):
    with lock:
        p=next((p for p in broker.positions if p['symbol']==req.symbol),None)
        if not p:raise HTTPException(404,'Pozisyon bulunamadı')
        broker.sell(p,p['current'],str(provider.get_index_data().index[-1].date()),'MANUAL DEMO EXIT');persist();return dashboard()
@app.post('/api/automation/{action}')
def automation(action:Literal['start','stop']):
    with lock:
        broker.auto=action=='start';persist();return dashboard()
@app.post('/api/scan')
async def manual_scan():
    await run_in_threadpool(scan,True);return dashboard()
@app.post('/api/reset')
def reset(req:Reset):
    global broker,cfg
    with lock:
        cfg=cfg.model_copy(update={'initial_balance':req.initial_balance});broker=PaperBroker(cfg)
        broker.record(str(provider.get_index_data().index[-1].date()));persist();return dashboard()
@app.get('/api/settings')
def settings():return cfg
@app.put('/api/settings')
def update_settings(req:Settings):
    global cfg
    with lock:
        cfg=req;broker.cfg=cfg;persist()
    scan();return cfg
@app.post('/api/backtest')
async def backtest(req:BacktestRequest):
    candidate=cfg.model_copy(update=req.model_dump(exclude={'start','end'}))
    snapshot=MockDataProvider();snapshot.cursor=provider.cursor
    try:result=await run_in_threadpool(run_backtest,snapshot,req.start,req.end,candidate)
    except (ValueError,KeyError) as exc:raise HTTPException(422,str(exc))
    with lock:backtests.append({'request':req.model_dump(),'result':result});persist()
    return result
@app.post('/api/optimization')
async def optimization(req:OptimizationRequest):
    candidate=cfg.model_copy(update=req.model_dump(exclude={'start','end','grid'}));snapshot=MockDataProvider();snapshot.cursor=provider.cursor
    try:return await run_in_threadpool(optimize,snapshot,req.start,req.end,candidate,req.grid)
    except (ValueError,KeyError) as exc:raise HTTPException(422,str(exc))
@app.websocket('/ws/market')
async def websocket(ws:WebSocket):
    if ws.headers.get('origin') not in ('http://localhost:3000','http://127.0.0.1:3000',None):
        await ws.close(code=1008);return
    await ws.accept()
    try:
        while True:
            with lock:payload=dashboard()
            await ws.send_json(payload);await asyncio.sleep(2)
    except WebSocketDisconnect:pass
