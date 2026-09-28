from typing import Protocol
import pandas as pd

class DataProvider(Protocol):
    def get_bist100_symbols(self) -> list[str]: ...
    def get_market_data(self) -> dict[str,pd.DataFrame]: ...
    def get_historical_data(self, symbol: str) -> pd.DataFrame: ...
    def get_latest_price(self, symbol: str) -> float: ...
    def get_index_data(self) -> pd.DataFrame: ...

def validate_candles(df: pd.DataFrame, expected_timestamp: pd.Timestamp, expected_index: pd.DatetimeIndex | None = None) -> None:
    required={'open','high','low','close','volume'}
    if not required.issubset(df.columns) or len(df)<210: raise ValueError('Eksik mum/geçmiş')
    if df.index.has_duplicates or not df.index.is_monotonic_increasing: raise ValueError('Tekrarlanan/sırasız mum')
    if df[list(required)].isna().any().any() or (df[['open','high','low','close']]<=0).any().any(): raise ValueError('Geçersiz fiyat')
    if (df.high < df[['open','close','low']].max(axis=1)).any() or (df.low > df[['open','close','high']].min(axis=1)).any(): raise ValueError('Geçersiz OHLC')
    if expected_index is not None and not df.index.equals(expected_index): raise ValueError('Eksik/fazla seans mumu')
    if df.index[-1] != expected_timestamp: raise ValueError('Eski veya geleceğe ait fiyat')
    # Provider must normalize to its exchange session calendar before validation.
    if (df.index.to_series().diff().dropna() > pd.Timedelta(days=4)).any(): raise ValueError('Eksik seans; veri sağlayıcısının takvimini kontrol edin')
