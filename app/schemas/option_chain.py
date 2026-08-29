from typing import List
from pydantic import BaseModel

from app.schemas.option_contract import OptionContract

class OptionChain(BaseModel):
    underlying: str
    contracts: List[OptionContract]