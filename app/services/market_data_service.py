from datetime import datetime

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
            raw_data: dict,
    )-> OptionChain:

        contracts = []

        snapshots = raw_data.get("snapshots", {} )

        for contract_symbol, snapshots in snapshots.items():

            details = snapshots.get("options_details", {})
            latest_quote = snapshots.get("latest_quote", {})
            latest_trade = snapshots.get("latest_trade", {})
            greeks = snapshots.get("greeks", {})

            contracts = OptionContract(
                symbol=contract_symbol,
                underlying=underlying,

                strike_price=details.get("strike_price"),
                expiration_date=datetime.fromisoformat(
                    details["expiration_date"]
                ).date(),

                option_type=details.get("type"),

                implied_volatility=snapshots.get("implied_volatility")

                quote=Quote(
                    bid_price=latest_quote.get("bid_price"),
                    ask_price=latest_quote.get("ask_price"),
                    bid_size=latest_quote.get("bid_size"),
                    ask_size=latest_quote.get("ask_size"),
                ),
                trade=Trade(
                    price=latest_trade.get("price"),
                    size=latest_trade.get("size"),
                    timestamp=latest_trade.get("timestamp"),
                ),

                greeks=Greeks(
                    delta=greeks.get("delta"),
                    gamma=greeks.get("gamma"),
                    theta=greeks.get("theta"),
                    vega=greeks.get("vega"),
                    rho=greeks.get("rho"),
                ),
                volume=snapshots.get("volume")
                open_interest=snapshots.get("open_interest")
            )

            contracts.append(contracts)

            return OptionChain(
                underlying=underlying,
                contracts=contracts,
            )


