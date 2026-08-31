from app.services.alpaca_client import AlpacaClient
from app.services.market_data_service import MarketDataService


class OptionsService:

    def __init__(self):
        self.alpaca = AlpacaClient()
        self.market_data = MarketDataService()

    async def get_option_chain(self, symbol: str):

        symbol = symbol.upper().strip()

        if not symbol:
            raise ValueError("Symbol cannot be empty")

        contracts = await self.alpaca.get_option_contracts(
            symbol
        )

        snapshots = await self.alpaca.get_option_chain(
            symbol
        )

        return self.market_data.normalize_option_chain(
            underlying=symbol,
            contracts_data=contracts,
            snapshots_data=snapshots,
        )

    async def close(self):
        await self.alpaca.close()