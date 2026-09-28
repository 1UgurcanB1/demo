from app.backtest.engine import run_backtest
from app.config import Settings
from itertools import product
import math

def objective(m):
    pf=min(m['profit_factor'] or (3 if m['net']>0 else 0),3)
    return m['return_pct']+5*pf+3*(m['sharpe'] or 0)-2*m['max_drawdown']+max(-5,min(5,m['expectancy']/100))

def optimize(provider,start,end,cfg,grid=None):
    dates=provider.get_index_data().loc[start:end].index
    if len(dates)<60:raise ValueError('Optimizasyon için en az 60 seans seçin')
    a=int(len(dates)*.5);b=int(len(dates)*.75)
    splits={'train':(str(dates[0].date()),str(dates[a-1].date())),'validation':(str(dates[a].date()),str(dates[b-1].date())),'test':(str(dates[b].date()),str(dates[-1].date()))}
    # Bounded grid; test is executed once, only after validation selection.
    grid=grid or {'min_score':[65,75],'atr_multiplier':[1.5,2.5]}
    allowed={'ema_fast','ema_slow','rsi_min','rsi_max','min_score','min_expected','min_rr','atr_multiplier','trailing_atr','partial_1','partial_2','target_rr1','target_rr2'}
    if not set(grid).issubset(allowed) or any(not v for v in grid.values()) or math.prod(len(v) for v in grid.values())>12:raise ValueError('Geçerli parametrelerle en çok 12 kombinasyon seçin')
    rows=[]
    for values in product(*grid.values()):
        params=dict(zip(grid,values)); candidate=Settings(**{**cfg.model_dump(),**params})
        train=run_backtest(provider,*splits['train'],candidate)['metrics']
        validation=run_backtest(provider,*splits['validation'],candidate)['metrics']
        rows.append({'params':params,'train':train,'validation':validation,'optimization_score':objective(validation)})
    rows.sort(key=lambda r:r['optimization_score'],reverse=True)
    best=cfg.model_copy(update=rows[0]['params'])
    test=run_backtest(provider,*splits['test'],best)
    return {'candidates':rows,'selected':rows[0]['params'],'test':test,'splits':splits,'note':f'{len(rows)} kombinasyon; seçim yalnızca validation sonucuyla yapılır. Test seçime katılmaz. Sentetik sonuçlar gerçek performans kanıtı değildir.'}
