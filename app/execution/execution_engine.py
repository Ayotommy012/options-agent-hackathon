from app.risk.risk_engine import RiskEngine
from app.schemas.trading_strategy import TradeCandidate
from app.services.alpaca_client import AlpacaClient


class ExecutionEngine:
    def __init__(
        self,
        alpaca_client: AlpacaClient,
        risk_engine: RiskEngine,
    ):
        self.alpaca_client = alpaca_client
        self.risk_engine = risk_engine

    async def execute_trade(
        self,
        candidate: TradeCandidate,
        current_total_risk: float = 0.0,
    ) -> list[dict]:

        approved = self.risk_engine.approve_trade(
            candidate,
            current_total_risk=current_total_risk,
        )

        if not approved:
            return []

        orders = []

        if len(candidate.legs) == 1:
            leg = candidate.legs[0]
            side = "buy" if leg.action.lower() == "buy" else "sell"
            order = await self.alpaca_client.submit_option_order(
                symbol=leg.symbol,
                quantity=leg.quantity,
                side=side,
            )
            orders.append(order)
        else:
            api_legs = []
            for leg in candidate.legs:
                side = "buy" if leg.action.lower() == "buy" else "sell"
                # Assuming opening a new position for now
                intent = "buy_to_open" if side == "buy" else "sell_to_open"
                api_legs.append({
                    "symbol": leg.symbol,
                    "side": side,
                    "position_intent": intent,
                    "ratio_qty": leg.quantity,
                })
            
            # Alpaca requires limit orders for multi-leg options
            # If net_debit is set, use it. If net_credit is set, use its negative value.
            limit_price = 0.0
            if candidate.net_debit is not None:
                limit_price = round(candidate.net_debit, 2)
            elif candidate.net_credit is not None:
                limit_price = round(-candidate.net_credit, 2)
                
            # Submit as a single multi-leg order
            order = await self.alpaca_client.submit_mleg_order(
                qty=1,  # 1 unit of the overall strategy
                legs=api_legs,
                order_type="limit",
                limit_price=limit_price
            )
            orders.append(order)

        return orders