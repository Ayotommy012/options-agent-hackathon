from typing import Optional

from pydantic import BaseModel

class OptionLeg(BaseModel):
    symbol: str
    option_type: str
    strike_price: float
    expiration_date: str
    action: str
    quantity: int = 1
    delta: Optional[float] = None

class TradeCandidate(BaseModel):
     underlying: str
     strategy: str

     legs: list[OptionLeg]

     max_profit: Optional[float] = None
     max_loss: Optional[float] = None
     breakeven: Optional[float] = None

     net_debit: Optional[float] = None
     net_credit: Optional[float] = None

     confidence: Optional[float] = None