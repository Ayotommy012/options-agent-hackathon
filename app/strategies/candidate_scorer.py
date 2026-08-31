from app.schemas.trading_strategy import TradeCandidate


class CandidateScorer:

    def score(self, candidate: TradeCandidate) -> float:
        """
        Score a trade candidate from 0 to 100.

        Current scoring focuses on:
        - risk/reward
        - maximum loss
        - defined-risk structure
        """

        score = 0.0

        # Risk/reward
        if (
            candidate.max_profit is not None
            and candidate.max_loss is not None
            and candidate.max_loss > 0
        ):
            reward_risk = (
                candidate.max_profit
                / candidate.max_loss
            )

            if reward_risk >= 3:
                score += 40
            elif reward_risk >= 2:
                score += 30
            elif reward_risk >= 1.5:
                score += 20
            elif reward_risk >= 1:
                score += 10

        # Prefer defined-risk trades
        if candidate.max_loss is not None:
            score += 20

        # Avoid excessively expensive trades
        if candidate.net_debit is not None:

            if candidate.net_debit <= 2:
                score += 20
            elif candidate.net_debit <= 5:
                score += 15
            elif candidate.net_debit <= 10:
                score += 10

        # Reward potential
        if candidate.max_profit is not None:

            if candidate.max_profit >= 500:
                score += 20
            elif candidate.max_profit >= 250:
                score += 15
            elif candidate.max_profit >= 100:
                score += 10

        # Probability of Profit (Delta edge)
        # For a debit spread, we want the long leg to be near the money (delta ~0.4 to 0.6)
        # This increases the probability that the spread actually pays out, stopping it from buying 1% lotto tickets.
        long_leg = next((leg for leg in candidate.legs if leg.action == "buy"), None)
        if long_leg and long_leg.delta is not None:
            delta = abs(long_leg.delta)
            if 0.40 <= delta <= 0.60:
                score += 30  # High probability ATM setup
            elif 0.30 <= delta < 0.40 or 0.60 < delta <= 0.70:
                score += 15  # Decent probability
            elif delta < 0.10:
                score -= 50  # Penalize extreme lottery tickets (10% or less probability)

        return min(max(score, 0.0), 100.0)

    def rank(
        self,
        candidates: list[TradeCandidate],
    ) -> list[TradeCandidate]:

        scored_candidates = []

        for candidate in candidates:

            candidate.confidence = self.score(candidate)

            scored_candidates.append(candidate)

        return sorted(
            scored_candidates,
            key=lambda candidate: candidate.confidence or 0,
            reverse=True,
        )