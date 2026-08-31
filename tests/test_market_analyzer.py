from datetime import date

from app.schemas.option_chain import OptionChain
from app.schemas.option_contract import (
    Greeks,
    OptionContract,
    Quote,
    Trade,
)
from app.strategies.market_analyzer import MarketAnalyzer


def make_contract(
    symbol: str,
    bid: float,
    ask: float,
    volume: int,
    open_interest: int,
):

    return OptionContract(
        symbol=symbol,
        underlying="AAPL",
        strike_price=250,
        expiration_date=date(2026, 9, 18),
        option_type="call",
        quote=Quote(
            bid_price=bid,
            ask_price=ask,
        ),
        trade=Trade(),
        greeks=Greeks(),
        volume=volume,
        open_interest=open_interest,
    )


def test_liquidity_filter():

    chain = OptionChain(
        underlying="AAPL",
        contracts=[
            make_contract(
                "GOOD",
                bid=5.00,
                ask=5.20,
                volume=100,
                open_interest=500,
            ),
            make_contract(
                "BAD",
                bid=5.00,
                ask=7.00,
                volume=100,
                open_interest=500,
            ),
        ],
    )

    analyzer = MarketAnalyzer()

    result = analyzer.liquid_contracts(chain)

    assert len(result) == 1
    assert result[0].symbol == "GOOD"