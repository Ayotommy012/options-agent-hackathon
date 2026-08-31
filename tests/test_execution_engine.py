import pytest

from app.execution.execution_engine import ExecutionEngine
from app.risk.risk_engine import RiskEngine
from app.schemas.trading_strategy import OptionLeg, TradeCandidate


class FakeAlpacaClient:
    def __init__(self):
        self.orders = []

    async def submit_option_order(
        self,
        symbol: str,
        quantity: int,
        side: str,
    ):
        order = {
            "symbol": symbol,
            "quantity": quantity,
            "side": side,
        }

        self.orders.append(order)
        return order

    async def submit_mleg_order(
        self,
        qty: int,
        legs: list[dict],
        order_type: str = "limit",
        limit_price: float | None = None,
    ):
        order = {
            "order_class": "mleg",
            "qty": qty,
            "legs": legs,
            "type": order_type,
            "limit_price": limit_price,
        }

        self.orders.append(order)
        return order


def make_candidate(
    max_profit: float,
    max_loss: float,
):
    return TradeCandidate(
        underlying="AAPL",
        strategy="bull_call_spread",
        legs=[
            OptionLeg(
                symbol="AAPL250C",
                option_type="call",
                strike_price=250,
                expiration_date="2026-09-18",
                action="buy",
                quantity=1,
            ),
            OptionLeg(
                symbol="AAPL260C",
                option_type="call",
                strike_price=260,
                expiration_date="2026-09-18",
                action="sell",
                quantity=1,
            ),
        ],
        max_profit=max_profit,
        max_loss=max_loss,
        net_debit=3.0,
    )


@pytest.mark.asyncio
async def test_execute_approved_trade():
    client = FakeAlpacaClient()
    risk_engine = RiskEngine()

    engine = ExecutionEngine(
        alpaca_client=client,
        risk_engine=risk_engine,
    )

    candidate = make_candidate(
        max_profit=1_000,
        max_loss=500,
    )

    orders = await engine.execute_trade(candidate)

    assert len(orders) == 1

    order = orders[0]

    assert order["order_class"] == "mleg"
    assert order["qty"] == 1
    assert order["type"] == "limit"
    assert order["limit_price"] == 3.0

    assert len(order["legs"]) == 2

    assert order["legs"][0]["symbol"] == "AAPL250C"
    assert order["legs"][0]["side"] == "buy"
    assert order["legs"][0]["position_intent"] == "buy_to_open"
    assert order["legs"][0]["ratio_qty"] == 1

    assert order["legs"][1]["symbol"] == "AAPL260C"
    assert order["legs"][1]["side"] == "sell"
    assert order["legs"][1]["position_intent"] == "sell_to_open"
    assert order["legs"][1]["ratio_qty"] == 1


@pytest.mark.asyncio
async def test_execute_trade_respects_quantity():
    client = FakeAlpacaClient()
    risk_engine = RiskEngine()

    engine = ExecutionEngine(
        alpaca_client=client,
        risk_engine=risk_engine,
    )

    candidate = make_candidate(
        max_profit=1_000,
        max_loss=500,
    )

    candidate.legs[0].quantity = 3

    orders = await engine.execute_trade(candidate)

    assert len(orders) == 1

    order = orders[0]

    assert order["legs"][0]["ratio_qty"] == 3
    assert order["legs"][1]["ratio_qty"] == 1


@pytest.mark.asyncio
async def test_rejects_risky_trade():
    client = FakeAlpacaClient()
    risk_engine = RiskEngine()

    engine = ExecutionEngine(
        alpaca_client=client,
        risk_engine=risk_engine,
    )

    candidate = make_candidate(
        max_profit=6_000,
        max_loss=3_000,
    )

    orders = await engine.execute_trade(candidate)

    assert orders == []
    assert client.orders == []


@pytest.mark.asyncio
async def test_rejects_bad_reward_risk():
    client = FakeAlpacaClient()
    risk_engine = RiskEngine()

    engine = ExecutionEngine(
        alpaca_client=client,
        risk_engine=risk_engine,
    )

    candidate = make_candidate(
        max_profit=500,
        max_loss=500,
    )

    orders = await engine.execute_trade(candidate)

    assert orders == []
    assert client.orders == []