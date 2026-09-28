from app.risk.manager import quantity,pause_reason
from app.backtest.metrics import metrics

class PaperBroker:
    def __init__(self,cfg):
        self.cfg=cfg; self.cash=cfg.initial_balance; self.initial=cfg.initial_balance; self.peak=self.cash; self.day_start=self.cash
        self.positions=[]; self.trades=[]; self.orders=[]; self.curve=[]; self.notifications=[]; self.paused=None; self.auto=False
    def equity(self): return self.cash+sum(p['quantity']*p['current'] for p in self.positions)
    def notify(self,kind,text): self.notifications=(self.notifications+[{'kind':kind,'text':text}])[-100:]
    def buy(self,signal,date,manual=False):
        reason=pause_reason(self.equity(),self.peak,self.day_start,self.cfg)
        if self.paused or reason: raise ValueError(self.paused or reason)
        if len(self.positions)>=self.cfg.max_positions: raise ValueError('Açık pozisyon limiti')
        if any(p['symbol']==signal['symbol'] for p in self.positions): raise ValueError('Bu hissede zaten pozisyon var')
        if not manual and not signal['eligible']: raise ValueError('Strateji filtreleri uygun değil')
        q=quantity(self.equity(),self.cash,signal['entry'],signal['stop'],self.cfg)
        if q<1: raise ValueError('Risk/nakit limiti nedeniyle lot alınamıyor')
        entry=signal['entry']*(1+self.cfg.slippage); fee=q*entry*self.cfg.commission
        self.cash-=q*entry+fee
        p={'symbol':signal['symbol'],'entry':entry,'current':signal['price'],'quantity':q,'original_quantity':q,'stop':signal['stop'],'target1':signal['target1'],'target2':signal['target2'],'high':entry,'stage':0,'buy_time':date,'entry_fee_per_share':fee/q,'trailing':False}
        self.positions.append(p); self.orders.append({'side':'BUY','symbol':p['symbol'],'quantity':q,'price':entry,'time':date,'commission':fee})
        self.notify('POSITION OPENED',f"{p['symbol']} · {q} lot")
    def sell(self,p,price,date,reason,q=None):
        q=min(q if q is not None else p['quantity'],p['quantity'])
        if q<1:return
        fill=price*(1-self.cfg.slippage); fee=fill*q*self.cfg.commission; gross=(fill-p['entry'])*q
        commission=fee+p['entry_fee_per_share']*q; net=gross-commission
        self.cash+=fill*q-fee; p['quantity']-=q
        self.trades.append({'symbol':p['symbol'],'buy_time':p['buy_time'],'sell_time':date,'buy_price':p['entry'],'sell_price':fill,'quantity':q,'gross':gross,'commission':commission,'net':net,'return_pct':net/(q*p['entry'])*100,'reason':reason})
        self.orders.append({'side':'SELL','symbol':p['symbol'],'quantity':q,'price':fill,'time':date,'commission':fee})
        if p['quantity']==0:self.positions.remove(p)
        self.notify('POSITION CLOSED' if p['quantity']==0 else 'TARGET HIT',f"{p['symbol']} · {reason}")
    def mark(self,bars,date,reset_day=True):
        if reset_day: self.day_start=self.equity()
        for p in self.positions.copy():
            r=bars[p['symbol']]; p['current']=float(r['close'])
            # Stops active before this bar win same-bar ambiguity; gap fills at opening price.
            if r['low']<=p['stop']:
                self.sell(p,min(r['open'],p['stop']),date,'TRAILING STOP' if p['trailing'] else 'STOP LOSS'); continue
            for stage,target,fraction in [(0,'target1',self.cfg.partial_1),(1,'target2',self.cfg.partial_2)]:
                if p in self.positions and p['stage']==stage and r['high']>=p[target]:
                    self.sell(p,p[target],date,'TAKE PROFIT',int(p['original_quantity']*fraction)); p['stage']+=1
                    p['stop']=max(p['stop'],(p['entry']+p['entry_fee_per_share'])/((1-self.cfg.slippage)*(1-self.cfg.commission)))
            if p not in self.positions:continue
            if r['close']<r.get('ema50',0):self.sell(p,r['close'],date,'TREND EXIT');continue
            p['high']=max(p['high'],r['high'])
            if p['stage']>0:
                old=p['stop']; p['stop']=max(old,min(p['high']-self.cfg.trailing_atr*r['atr'],r['close']*.999));p['trailing']=True
                if p['stop']>old:self.notify('STOP UPDATED',p['symbol'])
        self.peak=max(self.peak,self.equity())
        reason=pause_reason(self.equity(),self.peak,self.day_start,self.cfg)
        if reason:self.paused=reason;self.notify(reason,'Yeni işlemler durduruldu; koruyucu çıkışlar aktif')
    def record(self,date):
        value=self.equity(); self.peak=max(self.peak,value)
        self.curve.append({'date':date,'equity':value,'pnl':value-(self.curve[-1]['equity'] if self.curve else self.initial),'drawdown':(value/self.peak-1)*100})
    def summary(self):
        points=self.curve.copy()
        if points: points[-1]={**points[-1],'equity':self.equity()}
        else: points=[{'equity':self.equity()}]
        m=metrics(points,self.trades,self.initial)
        m['max_drawdown']=max(m['max_drawdown'],(1-self.equity()/self.peak)*100)
        return {**m,'equity':self.equity(),'cash':self.cash,'position_value':self.equity()-self.cash,'today_pnl':self.equity()-self.day_start,'open_count':len(self.positions),'auto':self.auto,'paused':self.paused,'notifications':self.notifications[-20:]}
