from app.schemas.trading_strategy import (
    OptionLeg,
    TradeCandidate,
)
from app.strategies.candidate_scorer import CandidateScorer


def test_candidate_scoring():

    candidate = TradeCandidate(
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
        max_profit=700,
        max_loss=300,
        breakeven=253,
        net_debit=3,
    )

    scorer = CandidateScorer()

    score = scorer.score(candidate)

    assert score == 85