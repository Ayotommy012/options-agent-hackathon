import httpx

from app.core.config import settings


class AlpacaClient:
    def __init__(self):
        self.client = httpx.AsyncClient(
            headers={
                "APCA-API-KEY-ID": settings.alpaca_api_key,
                "APCA-API-SECRET-KEY": settings.alpaca_api_secret,
            },
            timeout=30.0,
        )

    async def get_option_contracts(self, symbol: str):
        response = await self.client.get(
            "https://paper-api.alpaca.markets/v2/options/contracts",
            params={
                "underlying_symbols": symbol,
                "limit": 100,
            },
        )

        response.raise_for_status()

        return response.json()

    async def get_option_chain(self, symbol: str):
        response = await self.client.get(
            f"{settings.alpaca_data_url}/v1beta1/options/snapshots/{symbol}",
            params={
                "limit": 100,
            },
        )

        response.raise_for_status()

        return response.json()

    async def submit_option_order(
        self,
        symbol: str,
        quantity: int,
        side: str,
    ):
        response = await self.client.post(
            f"{settings.alpaca_trading_url}/v2/orders",
            json={
                "symbol": symbol,
                "qty": quantity,
                "side": side,
                "type": "market",
                "time_in_force": "day",
            },
        )

        response.raise_for_status()

        return response.json()

    async def submit_mleg_order(
        self,
        qty: int,
        legs: list,
        order_type: str = "market",
        limit_price: float = None,
    ):
        payload = {
            "order_class": "mleg",
            "type": order_type,
            "time_in_force": "day",
            "qty": qty,
            "legs": legs,
        }
        if limit_price is not None:
            payload["limit_price"] = str(limit_price)
            
        response = await self.client.post(
            f"{settings.alpaca_trading_url}/v2/orders",
            json=payload,
        )

        response.raise_for_status()

        return response.json()

    async def get_account(self):
        response = await self.client.get(
            f"{settings.alpaca_trading_url}/v2/account"
        )
        response.raise_for_status()
        return response.json()

    async def get_positions(self):
        response = await self.client.get(
            f"{settings.alpaca_trading_url}/v2/positions"
        )
        response.raise_for_status()
        return response.json()

    async def get_orders(self, status: str = "open"):
        response = await self.client.get(
            f"{settings.alpaca_trading_url}/v2/orders",
            params={"status": status, "nested": "true"}
        )
        response.raise_for_status()
        return response.json()

    async def close_position(self, symbol_or_id: str):
        response = await self.client.delete(
            f"{settings.alpaca_trading_url}/v2/positions/{symbol_or_id}"
        )
        response.raise_for_status()
        return response.json()

    async def close(self):
        await self.client.aclose()