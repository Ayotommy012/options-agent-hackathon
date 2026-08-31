from app.schemas.trading_strategy import (
    OptionLeg,
    TradeCandidate,
)
from app.risk.risk_engine import RiskEngine


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
            ),
            OptionLeg(
                symbol="AAPL260C",
                option_type="call",
                strike_price=260,
                expiration_date="2026-09-18",
                action="sell",
            ),
        ],
        max_profit=max_profit,
        max_loss=max_loss,
        net_debit=3,
    )


def test_acceptable_trade():

    engine = RiskEngine(
        account_size=100_000,
    )

    candidate = make_candidate(
        max_profit=1_000,
        max_loss=500,
    )

    assert engine.approve_trade(candidate)


def test_rejects_excessive_loss():

    engine = RiskEngine(
        account_size=100_000,
    )

    candidate = make_candidate(
        max_profit=6_000,
        max_loss=3_000,
    )

    assert not engine.approve_trade(candidate)


def test_rejects_bad_reward_risk():

    engine = RiskEngine(
        account_size=100_000,
    )

    candidate = make_candidate(
        max_profit=500,
        max_loss=500,
    )

    assert not engine.approve_trade(candidate)


def test_rejects_excessive_total_risk():

    engine = RiskEngine(
        account_size=100_000,
    )

    candidate = make_candidate(
        max_profit=1_000,
        max_loss=500,
    )

    assert not engine.approve_trade(
        candidate,
        current_total_risk=9_600,
    )