from datetime import date
from typing import Optional

from pydantic import BaseModel

class Greeks(BaseModel):
    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None
    vega: Optional[float] = None
    rho: Optional[float] = None

class Quote(BaseModel):
    bid_price:Optional[float] = None
    ask_price: Optional[float] = None
    bid_size: Optional[int] = None
    ask_size: Optional[int] = None

class Trade(BaseModel):
    price: Optional[float] = None
    size: Optional[int] = None
    timestamp: Optional[str] = None

class OptionContract(BaseModel):
    symbol: str
    underlying: str

    strike_price: float
    expiration_date: date
    option_type: str

    implied_volatility: Optional[float] = None

    quote: Quote
    trade: Trade
    greeks: Greeks

    volume: Optional[int] = None
    open_interest:Optional[int] = None