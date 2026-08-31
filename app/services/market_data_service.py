from datetime import date

from app.schemas.option_chain import OptionChain
from app.schemas.option_contract import (
    Greeks,
    OptionContract,
    Quote,
    Trade,
)


class MarketDataService:

    def normalize_option_chain(
        self,
        underlying: str,
        contracts_data: dict,
        snapshots_data: dict,
    ) -> OptionChain:

        contracts = []

        contract_list = contracts_data.get("option_contracts", [])
        snapshots = snapshots_data.get("snapshots", {})

        for contract in contract_list:

            symbol = contract.get("symbol")

            snapshot = snapshots.get(symbol, {})

            latest_quote = snapshot.get("latestQuote", {})
            latest_trade = snapshot.get("latestTrade", {})
            greeks = snapshot.get("greeks", {})

            expiration = contract.get("expiration_date")

            if not expiration:
                continue

            option = OptionContract(
                symbol=symbol,
                underlying=underlying,

                strike_price=float(
                    contract.get("strike_price", 0)
                ),

                expiration_date=date.fromisoformat(
                    expiration
                ),

                option_type=contract.get("type", "").lower(),

                implied_volatility=snapshot.get(
                    "impliedVolatility"
                ),

                quote=Quote(
                    bid_price=latest_quote.get("bp"),
                    ask_price=latest_quote.get("ap"),
                    bid_size=latest_quote.get("bs"),
                    ask_size=latest_quote.get("as"),
                ),

                trade=Trade(
                    price=latest_trade.get("p"),
                    size=latest_trade.get("s"),
                    timestamp=latest_trade.get("t"),
                ),

                greeks=Greeks(
                    delta=greeks.get("delta"),
                    gamma=greeks.get("gamma"),
                    theta=greeks.get("theta"),
                    vega=greeks.get("vega"),
                    rho=greeks.get("rho"),
                ),

                volume=snapshot.get("volume"),
                open_interest=snapshot.get("openInterest"),
            )

            contracts.append(option)

        return OptionChain(
            underlying=underlying,
            contracts=contracts,
        )