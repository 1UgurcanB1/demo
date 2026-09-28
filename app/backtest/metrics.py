import numpy as np

def metrics(curve,trades,initial):
    values=np.array([p['equity'] for p in curve] or [initial],dtype=float)
    returns=np.diff(values)/values[:-1] if len(values)>1 else np.array([])
    pnls=[t['net'] for t in trades]; wins=[x for x in pnls if x>0]; losses=[x for x in pnls if x<0]
    drawdown=values/np.maximum.accumulate(values)-1
    days=max(1,len(values)-1)
    return {'initial':initial,'final':float(values[-1]),'net':float(values[-1]-initial),'return_pct':float((values[-1]/initial-1)*100),'annualized':float(((values[-1]/initial)**(252/days)-1)*100),'max_drawdown':float(-drawdown.min()*100),'win_rate':len(wins)/len(pnls)*100 if pnls else 0,'profit_factor':sum(wins)/abs(sum(losses)) if losses else None,'sharpe':float(returns.mean()/returns.std()*np.sqrt(252)) if len(returns)>1 and returns.std()>0 else None,'total_trades':len(trades),'average_trade':float(np.mean(pnls)) if pnls else 0,'average_winner':float(np.mean(wins)) if wins else 0,'average_loser':float(np.mean(losses)) if losses else 0,'best_trade':max(pnls,default=0),'worst_trade':min(pnls,default=0),'expectancy':float(np.mean(pnls)) if pnls else 0}
