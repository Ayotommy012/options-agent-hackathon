from app.schemas.trading_strategy import TradeCandidate


class RiskEngine:
    def __init__(
        self,
        account_size: float = 100_000,
        max_risk_per_trade_percent: float = 2.0,
        max_total_risk_percent: float = 10.0,
        min_reward_risk: float = 1.5,
    ):
        self.account_size = account_size
        self.max_risk_per_trade = (
            account_size * max_risk_per_trade_percent / 100
        )
        self.max_total_risk = (
            account_size * max_total_risk_percent / 100
        )
        self.min_reward_risk = min_reward_risk

    def approve_trade(
        self,
        candidate: TradeCandidate,
        current_total_risk: float = 0.0,
    ) -> bool:

        if candidate.max_loss is None:
            return False

        if candidate.max_profit is None:
            return False

        if candidate.max_loss <= 0:
            return False

        reward_risk = (
            candidate.max_profit
            / candidate.max_loss
        )

        if reward_risk < self.min_reward_risk:
            return False

        if candidate.max_loss > self.max_risk_per_trade:
            return False

        if (
            current_total_risk + candidate.max_loss
            > self.max_total_risk
        ):
            return False

        return True
    