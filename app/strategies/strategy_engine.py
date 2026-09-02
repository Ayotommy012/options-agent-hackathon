from datetime import date
from app.schemas.option_chain import OptionChain
from app.schemas.trading_strategy import (
    OptionLeg,
    TradeCandidate,
)


class StrategyEngine:
    def _filter_by_dte(self, contracts, min_days=30, max_days=90):
        filtered = []
        today = date.today()
        for contract in contracts:
            dte = (contract.expiration_date - today).days
            if min_days <= dte <= max_days:
                filtered.append(contract)
        return filtered

    def find_bull_call_spreads(
        self,
        chain: OptionChain,
    ) -> list[TradeCandidate]:

        calls = [
            contract
            for contract in chain.contracts
            if contract.option_type.lower() == "call"
        ]
        
        # Prevent 0DTE lottery tickets
        calls = self._filter_by_dte(calls)

        candidates = []

        for long_call in calls:

            for short_call in calls:

                if short_call.strike_price <= long_call.strike_price:
                    continue

                if short_call.expiration_date != long_call.expiration_date:
                    continue

                if (
                    long_call.quote.ask_price is None
                    or short_call.quote.bid_price is None
                ):
                    continue

                debit = (
                    long_call.quote.ask_price
                    - short_call.quote.bid_price
                )

                if debit <= 0:
                    continue

                spread_width = (
                    short_call.strike_price
                    - long_call.strike_price
                )

                max_loss = debit * 100

                max_profit = (
                    spread_width - debit
                ) * 100

                breakeven = (
                    long_call.strike_price + debit
                )

                candidates.append(
                    TradeCandidate(
                        underlying=chain.underlying,
                        strategy="bull_call_spread",
                        legs=[
                            OptionLeg(
                                symbol=long_call.symbol,
                                option_type="call",
                                strike_price=long_call.strike_price,
                                expiration_date=str(
                                    long_call.expiration_date
                                ),
                                action="buy",
                                delta=long_call.greeks.delta if long_call.greeks else None,
                            ),
                            OptionLeg(
                                symbol=short_call.symbol,
                                option_type="call",
                                strike_price=short_call.strike_price,
                                expiration_date=str(
                                    short_call.expiration_date
                                ),
                                action="sell",
                                delta=short_call.greeks.delta if short_call.greeks else None,
                            ),
                        ],
                        max_profit=max_profit,
                        max_loss=max_loss,
                        breakeven=breakeven,
                        net_debit=debit,
                    )
                )

        return candidates

    def find_bear_put_spreads(
        self,
        chain: OptionChain,
    ) -> list[TradeCandidate]:

        puts = [
            contract
            for contract in chain.contracts
            if contract.option_type.lower() == "put"
        ]
        
        # Prevent 0DTE lottery tickets
        puts = self._filter_by_dte(puts)

        candidates = []

        for long_put in puts:

            for short_put in puts:

                if short_put.strike_price >= long_put.strike_price:
                    continue

                if short_put.expiration_date != long_put.expiration_date:
                    continue

                if (
                    long_put.quote.ask_price is None
                    or short_put.quote.bid_price is None
                ):
                    continue

                debit = (
                    long_put.quote.ask_price
                    - short_put.quote.bid_price
                )

                if debit <= 0:
                    continue

                spread_width = (
                    long_put.strike_price
                    - short_put.strike_price
                )

                max_loss = debit * 100

                max_profit = (
                    spread_width - debit
                ) * 100

                breakeven = (
                    long_put.strike_price - debit
                )

                candidates.append(
                    TradeCandidate(
                        underlying=chain.underlying,
                        strategy="bear_put_spread",
                        legs=[
                            OptionLeg(
                                symbol=long_put.symbol,
                                option_type="put",
                                strike_price=long_put.strike_price,
                                expiration_date=str(
                                    long_put.expiration_date
                                ),
                                action="buy",
                                delta=long_put.greeks.delta if long_put.greeks else None,
                            ),
                            OptionLeg(
                                symbol=short_put.symbol,
                                option_type="put",
                                strike_price=short_put.strike_price,
                                expiration_date=str(
                                    short_put.expiration_date
                                ),
                                action="sell",
                                delta=short_put.greeks.delta if short_put.greeks else None,
                            ),
                        ],
                        max_profit=max_profit,
                        max_loss=max_loss,
                        breakeven=breakeven,
                        net_debit=debit,
                    )
                )

        return candidates