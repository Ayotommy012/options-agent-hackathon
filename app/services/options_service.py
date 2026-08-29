from app.services.alpaca_client import AlpacaClient

class OptionsService:
    def __init__(self):
        self.alpaca = AlpacaClient()

    async def get_option_chain(self, symbol:str):
        symbol = symbol.upper().strip()


        if not symbol:
            raise ValueError("Symbol cannot be empty")

        return await self.alpaca.get_option_chain(symbol)
    async def  close(self):
        await self.alpaca.close()