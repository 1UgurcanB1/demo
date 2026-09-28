import math

def quantity(equity: float,cash: float,entry: float,stop: float,cfg) -> int:
    cost=entry*(1+cfg.slippage)*(1+cfg.commission)
    risk=entry*(1+cfg.slippage)-stop*(1-cfg.slippage)+cfg.commission*(entry+stop)
    if risk<=0 or cash<=0: return 0
    return max(0,math.floor(min(equity*cfg.risk_per_trade/risk,equity*cfg.max_position_size/cost,cash/cost)))

def pause_reason(equity,peak,day_start,cfg):
    if equity<=peak*(1-cfg.max_drawdown): return 'MAX DRAWDOWN WARNING'
    if equity<=day_start*(1-cfg.daily_loss_limit): return 'DAILY LOSS LIMIT'
    return None
