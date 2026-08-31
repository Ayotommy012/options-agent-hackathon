from app.schemas.option_chain import OptionChain
from app.schemas.option_contract import OptionContract


class MarketAnalyzer:

    def liquid_contracts(
        self,
        chain: OptionChain,
        max_spread_percent: float = 10.0,
        min_volume: int = 10,
        min_open_interest: int = 50,
    ) -> list[OptionContract]:

        liquid = []

        for contract in chain.contracts:

            quote = contract.quote

            if (
                quote.bid_price is None
                or quote.ask_price is None
            ):
                continue

            if quote.bid_price <= 0:
                continue

            spread_percent = (
                (quote.ask_price - quote.bid_price)
                / quote.bid_price
            ) * 100

            if spread_percent > max_spread_percent:
                continue

            if (
                contract.volume is not None
                and contract.volume < min_volume
            ):
                continue

            if (
                contract.open_interest is not None
                and contract.open_interest < min_open_interest
            ):
                continue

            liquid.append(contract)

        return liquid