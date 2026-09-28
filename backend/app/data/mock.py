import hashlib
import numpy as np
import pandas as pd

NAMES='ASELS THYAO TUPRS BIMAS AKBNK GARAN ISCTR YKBNK SAHOL KCHOL SISE EREGL FROTO TOASO TCELL TTKOM ENKAI KOZAL KOZAA PETKM SASA HEKTS ASTOR ALFAS EUPWR GESAN KONTR MIATK REEDR ALTNY TAVHL PGSUS DOAS ARCLK VESTL VESBE MGROS SOKM BIZIM ULKER CCOLA AEFES TABGD MAVI KOTON DEVA ECILC EGEEN OTKAR TTRAK CIMSA AKCNS OYAKC BUCIM GOLTS KONYA BTCIM AKSEN ENJSA ENERY ZOREN ODAS AKFYE GWIND CWENE SMRTG KAYSE KCAER KRDMD IZMDC CEMTS BRSAN BORLS AGHOL ALARK DOHOL GLYHO TKFEN ENTRA EKGYO ISGYO TRGYO SNGYO OZKGY AKSGY YEOTK TURSG ANSGR ANHYT AGESA TSKB SKBNK HALKB VAKBN ISMEN INFO OYAYO EFORC OBAMS LMKDC'.split()

class MockDataProvider:
    """Reproducible synthetic daily bars. Names are illustrative, not current constituents."""
    def __init__(self):
        self.cursor=650
        self.frames={s:self._generate(s) for s in NAMES+['XU100']}
    def _generate(self,s: str) -> pd.DataFrame:
        rng=np.random.default_rng(int(hashlib.sha256(s.encode()).hexdigest()[:8],16))
        n=2500; t=np.arange(n)
        returns=.00025+.002*np.sin(t/37)+rng.normal(0,.014,n)
        c=(100 if s!='XU100' else 9000)*np.exp(np.cumsum(returns))
        o=np.r_[c[0],c[:-1]]*(1+rng.normal(0,.002,n))
        spread=rng.uniform(.003,.022,n)
        return pd.DataFrame({'open':o,'high':np.maximum(o,c)*(1+spread),'low':np.minimum(o,c)*(1-spread),'close':c,'volume':rng.integers(500000,9000000,n)},index=pd.bdate_range('2023-01-02',periods=n))
    def get_bist100_symbols(self): return NAMES.copy()
    def get_historical_data(self,symbol): return self.frames[symbol].iloc[:self.cursor].copy()
    def get_market_data(self): return {s:self.get_historical_data(s) for s in NAMES}
    def get_latest_price(self,symbol): return float(self.frames[symbol].iloc[self.cursor-1].close)
    def get_index_data(self): return self.get_historical_data('XU100')
    def advance(self): self.cursor=min(self.cursor+1,2500)
