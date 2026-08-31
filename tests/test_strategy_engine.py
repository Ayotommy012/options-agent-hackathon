from datetime import date

from app.schemas.option_chain import OptionChain
from app.schemas.option_contract import (
    Greeks,
    OptionContract,
    Quote,
    Trade,
)
from app.strategies.strategy_engine import StrategyEngine


def make_contract(
    symbol: str,
    strike: float,
    option_type: str,
    ask: float,
    bid: float,
):
    return OptionContract(
        symbol=symbol,
        underlying="AAPL",
        strike_price=strike,
        expiration_date=date(2026, 9, 18),
        option_type=option_type,
        implied_volatility=0.30,
        quote=Quote(
            bid_price=bid,
            ask_price=ask,
        ),
        trade=Trade(),
        greeks=Greeks(),
    )


def test_bull_call_spread():

    chain = OptionChain(
        underlying="AAPL",
        contracts=[
            make_contract(
                "AAPL250C",
                250,
                "call",
                ask=5.0,
                bid=4.8,
            ),
            make_contract(
                "AAPL260C",
                260,
                "call",
                ask=2.5,
                bid=2.0,
            ),
        ],
    )

    engine = StrategyEngine()

    candidates = engine.find_bull_call_spreads(chain)

    assert len(candidates) == 1

    spread = candidates[0]

    assert spread.strategy == "bull_call_spread"
    assert spread.net_debit == 3.0
    assert spread.max_loss == 300
    assert spread.max_profit == 700
    assert spread.breakeven == 253