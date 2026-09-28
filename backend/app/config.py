from pydantic import BaseModel, Field, model_validator

class Settings(BaseModel):
    initial_balance: float = Field(100000, ge=1000, le=1e9)
    risk_per_trade: float = Field(.01, gt=0, le=.05)
    max_position_size: float = Field(.10, gt=0, le=1)
    max_positions: int = Field(5, ge=1, le=30)
    daily_loss_limit: float = Field(.02, gt=0, le=.5)
    max_drawdown: float = Field(.10, gt=0, le=.9)
    min_score: float = Field(70, ge=0, le=100)
    min_expected: float = Field(60, ge=0, le=100)
    min_rr: float = Field(2, ge=1, le=10)
    atr_multiplier: float = Field(2, ge=.5, le=6)
    trailing_atr: float = Field(2.5, ge=.5, le=8)
    target_rr1: float = Field(2, ge=.5, le=8)
    target_rr2: float = Field(3.5, ge=1, le=15)
    partial_1: float = Field(.30, ge=0, le=.8)
    partial_2: float = Field(.30, ge=0, le=.8)
    scanner_interval: int = Field(60, ge=10, le=3600)
    commission: float = Field(.001, ge=0, le=.02)
    slippage: float = Field(.0005, ge=0, le=.02)
    ema_fast: int = Field(20, ge=5, le=60)
    ema_slow: int = Field(50, ge=21, le=150)
    rsi_min: float = Field(45, ge=10, le=70)
    rsi_max: float = Field(72, ge=40, le=90)
    weights: dict[str,float] = {'trend':25,'momentum':20,'volume':15,'action':15,'rr':15,'market':10}
    @model_validator(mode='after')
    def validate_combination(self):
        if self.target_rr1 >= self.target_rr2: raise ValueError('Hedef 2, hedef 1 üzerinde olmalı')
        if self.partial_1+self.partial_2 > .9: raise ValueError('Kısmi çıkışların toplamı en fazla %90 olabilir')
        if self.ema_fast >= self.ema_slow or self.rsi_min >= self.rsi_max: raise ValueError('Eşik sıralaması geçersiz')
        if set(self.weights) != {'trend','momentum','volume','action','rr','market'} or any(v<0 for v in self.weights.values()) or abs(sum(self.weights.values())-100)>1e-6: raise ValueError('Skor ağırlıkları toplamı 100 olmalı')
        return self
