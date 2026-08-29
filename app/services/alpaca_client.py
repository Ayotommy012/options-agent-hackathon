import httpx

from app.core.config import settings


class AlpacaClient:
    def __init__(self):
        self.client = httpx.AsyncClient(
            base_url = settings.alpaca_data_url,
            headers={
                "APCA-API-KEY-ID": settings.alpaca_api_key,
                "APCA-API-SECRET-KEY": settings.alpaca_api_secret,
            },
            timeout=30.0,
        )
    async def get_option_chain(self, symbol: str):
        response = await self.client.get(
            f"/v1beta1/options/snapshots/{symbol}",
            params={
                "limit":100,
            },
        )

        response.raise_for_status()

        return response.json()
    
    async def close(self):
        await self.client.aclose()