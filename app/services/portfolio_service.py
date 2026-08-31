from typing import Dict, Any
from app.services.alpaca_client import AlpacaClient


class PortfolioService:
    def __init__(self, alpaca_client: AlpacaClient):
        self.client = alpaca_client
        
    async def get_portfolio_state(self) -> Dict[str, Any]:
        """
        Fetches the current account, positions, and open orders.
        Calculates buying power, current risk exposure, and active symbols.
        """
        account = await self.client.get_account()
        positions = await self.client.get_positions()
        orders = await self.client.get_orders(status="open")
        
        active_symbols = set()
        current_exposure = 0.0
        
        # Calculate exposure from open positions
        for pos in positions:
            symbol = pos.get("symbol")
            active_symbols.add(symbol)
            
            # Absolute market value as a rough exposure estimate
            market_value = abs(float(pos.get("market_value", 0)))
            current_exposure += market_value
            
        # Add symbols from open orders
        for order in orders:
            symbol = order.get("symbol")
            active_symbols.add(symbol)
            
        return {
            "cash": float(account.get("cash", 0)),
            "equity": float(account.get("equity", 0)),
            "buying_power": float(account.get("buying_power", 0)),
            "current_exposure": current_exposure,
            "active_symbols": active_symbols,
            "positions_count": len(positions),
            "orders_count": len(orders),
            "raw_positions": positions,
            "raw_orders": orders,
        }
