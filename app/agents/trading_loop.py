import asyncio
import logging
import httpx
from typing import List

from app.core.config import settings
from app.services.alpaca_client import AlpacaClient
from app.services.options_service import OptionsService
from app.services.portfolio_service import PortfolioService
from app.strategies.strategy_engine import StrategyEngine
from app.strategies.candidate_scorer import CandidateScorer
from app.risk.risk_engine import RiskEngine
from app.execution.execution_engine import ExecutionEngine
from app.agents.decision_agent import DecisionAgent

logger = logging.getLogger("TradingLoop")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

class TradingLoop:
    def __init__(self):
        self.alpaca_client = AlpacaClient()
        self.options_service = OptionsService()
        self.portfolio_service = PortfolioService(self.alpaca_client)
        self.strategy_engine = StrategyEngine()
        self.scorer = CandidateScorer()
        self.risk_engine = RiskEngine()
        self.execution = ExecutionEngine(self.alpaca_client, self.risk_engine)
        self.ai_agent = DecisionAgent()
        
        # We can dynamically pull these from a watchlist database in the future
        self.symbols_to_monitor = ["SPY", "QQQ", "AAPL", "MSFT"]
        
    async def track_pnl_and_monitor_positions(self, state):
        positions = state.get("raw_positions", [])
        total_unrealized_pnl = 0.0
        
        logger.info(f"Currently tracking {len(positions)} open positions.")
        
        for pos in positions:
            symbol = pos.get("symbol")
            
            # Use 0 if the values are None or missing
            try:
                unrealized_pl = float(pos.get("unrealized_pl") or 0)
                unrealized_plpc = float(pos.get("unrealized_plpc") or 0)
            except ValueError:
                unrealized_pl = 0.0
                unrealized_plpc = 0.0
                
            total_unrealized_pnl += unrealized_pl
            
            # Simple take profit / stop loss logic for position monitoring
            if unrealized_plpc > 0.50:  # 50% profit
                logger.info(f"TAKE PROFIT triggered on {symbol} (+{unrealized_plpc*100:.1f}%)")
                try:
                    await self.alpaca_client.close_position(symbol)
                    logger.info(f"Successfully closed {symbol}.")
                except Exception as e:
                    logger.error(f"Failed to close {symbol}: {e}")
                    
            elif unrealized_plpc < -0.30:  # 30% stop loss
                logger.info(f"STOP LOSS triggered for {symbol} ({unrealized_plpc*100:.1f}%)")
                try:
                    await self.alpaca_client.close_position(symbol)
                    logger.info(f"Successfully closed {symbol}.")
                except Exception as e:
                    logger.error(f"Failed to close {symbol}: {e}")
                
        logger.info(f"Portfolio Equity: ${state['equity']} | Unrealized P&L: ${total_unrealized_pnl:.2f}")
        
    async def get_sentiment(self, symbol: str) -> str:
        """Fetch latest news and use Ollama to gauge sentiment to establish directional edge."""
        try:
            # Requires data API url, but we can just use the trading client for simplicity 
            # if we use the right base URL. Actually, the best way is using the raw httpx client.
            url = f"https://data.alpaca.markets/v1beta1/news?symbols={symbol}&limit=3"
            response = await self.alpaca_client.client.get(url)
            news_data = response.json().get("news", [])
            headlines = "\n".join([n.get("headline", "") for n in news_data])
            
            if not headlines:
                return "NEUTRAL"
                
            # Ask OpenRouter for directional edge
            prompt = f"Analyze these recent headlines for {symbol} and return exactly one word (BULLISH, BEARISH, or NEUTRAL):\n{headlines}"
            
            try:
                res = await self.ai_agent.client.chat.completions.create(
                    model=self.ai_agent.model_name,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                )
                content = res.choices[0].message.content.strip().upper()
                
                if "BULLISH" in content: return "BULLISH"
                if "BEARISH" in content: return "BEARISH"
                return "NEUTRAL"
            except Exception as e:
                logger.error(f"OpenRouter Sentiment error for {symbol}: {e}")
                return "NEUTRAL"
        except Exception as e:
            logger.error(f"Error fetching sentiment for {symbol}: {e}")
            return "NEUTRAL"
            
    async def get_ict_trend(self, symbol: str) -> str:
        """Fetch historical bars and use LLM to perform ICT (Inner Circle Trader) Smart Money analysis."""
        try:
            from datetime import datetime, timedelta, timezone
            start_date = (datetime.now(timezone.utc) - timedelta(days=20)).strftime('%Y-%m-%dT%H:%M:%SZ')
            url = f"https://data.alpaca.markets/v2/stocks/bars?symbols={symbol}&timeframe=1Day&start={start_date}&limit=15"
            response = await self.alpaca_client.client.get(url)
            bars = response.json().get("bars", {}).get(symbol, [])
            
            if len(bars) < 5:
                return "NEUTRAL"
                
            # Format OHLC data for the LLM
            price_action = ""
            for i, b in enumerate(bars[-10:]):
                price_action += f"Day {i+1} -> Open: {b.get('o'):.2f}, High: {b.get('h'):.2f}, Low: {b.get('l'):.2f}, Close: {b.get('c'):.2f}, Vol: {b.get('v')}\n"
                
            prompt = (
                f"You are an expert in Inner Circle Trader (ICT) and Smart Money Concepts (SMC).\n"
                f"Analyze the following recent daily price action for {symbol}:\n{price_action}\n"
                f"Look for Liquidity Sweeps, Fair Value Gaps (FVG), Order Blocks, and Market Structure Shifts (MSS).\n"
                f"Return EXACTLY one word (BULLISH, BEARISH, or NEUTRAL)."
            )
            
            res = await self.ai_agent.client.chat.completions.create(
                model=self.ai_agent.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
            )
            content = res.choices[0].message.content.strip().upper()
            
            if "BULLISH" in content: return "BULLISH"
            if "BEARISH" in content: return "BEARISH"
            return "NEUTRAL"
            
        except Exception as e:
            logger.error(f"Error fetching ICT trend for {symbol}: {e}")
            return "NEUTRAL"

    async def get_macro_regime(self) -> str:
        """Fetch general market news and apply Bridgewater Associates macro framework."""
        try:
            # Fetch general market news (SPY is a good proxy for macro news)
            url = f"https://data.alpaca.markets/v1beta1/news?symbols=SPY&limit=5"
            response = await self.alpaca_client.client.get(url)
            news_data = response.json().get("news", [])
            headlines = "\n".join([n.get("headline", "") for n in news_data])
            
            prompt = (
                "You are a Senior Macro Portfolio Manager at Bridgewater Associates. "
                "Apply Ray Dalio's macroeconomic frameworks (Growth vs Inflation expectations). "
                f"Analyze these recent market headlines:\n{headlines}\n"
                "Determine the current macro regime and how it impacts US Equities. "
                "Return EXACTLY one word representing your equity outlook: BULLISH, BEARISH, or NEUTRAL."
            )
            
            res = await self.ai_agent.client.chat.completions.create(
                model=self.ai_agent.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
            )
            content = res.choices[0].message.content.strip().upper()
            
            if "BULLISH" in content: return "BULLISH"
            if "BEARISH" in content: return "BEARISH"
            return "NEUTRAL"
        except Exception as e:
            logger.error(f"Error fetching macro regime: {e}")
            return "NEUTRAL"

    def get_position_direction(self, symbol: str, positions: list) -> str:
        """Determines if current exposure on a symbol is BULLISH or BEARISH based on option types."""
        import re
        for pos in positions:
            pos_symbol = pos.get("symbol", "")
            match = re.match(r"^[A-Z]+", pos_symbol)
            if match and match.group(0) == symbol:
                if "C" in pos_symbol: return "BULLISH"
                if "P" in pos_symbol: return "BEARISH"
        return "NEUTRAL"

    async def close_underlying_positions(self, underlying_symbol: str, raw_positions: list):
        import re
        for pos in raw_positions:
            pos_symbol = pos.get("symbol", "")
            match = re.match(r"^[A-Z]+", pos_symbol)
            if match and match.group(0) == underlying_symbol:
                logger.info(f"Closing position {pos_symbol} for underlying {underlying_symbol}")
                if settings.trading_enabled:
                    try:
                        await self.alpaca_client.close_position(pos_symbol)
                    except Exception as e:
                        logger.error(f"Failed to close {pos_symbol}: {e}")
                else:
                    logger.info(f"TRADING_ENABLED=false. Simulating close of {pos_symbol}.")

    async def step(self):
        logger.info("--- Starting Trading Loop Step ---")
        
        try:
            # 0. Bridgewater Macro Assessment
            macro_outlook = await self.get_macro_regime()
            logger.info(f"Bridgewater Macro Regime Outlook: {macro_outlook}")
            
            # 1. Get State
            state = await self.portfolio_service.get_portfolio_state()
            
            # Update RiskEngine dynamically with live equity
            self.risk_engine.account_size = state["equity"]
            self.risk_engine.max_risk_per_trade = state["equity"] * 0.02
            self.risk_engine.max_total_risk = state["equity"] * 0.10
            
            # 2. Position Monitoring & P&L
            await self.track_pnl_and_monitor_positions(state)
            
            # 3. Discover new trades and Re-evaluate open positions
            for symbol in self.symbols_to_monitor:
                logger.info(f"Analyzing {symbol} for opportunities/re-evaluation...")
                
                try:
                    news_sentiment = await self.get_sentiment(symbol)
                    ict_trend = await self.get_ict_trend(symbol)
                    logger.info(f"Signals for {symbol} -> Macro: {macro_outlook} | News: {news_sentiment} | ICT Smart Money: {ict_trend}")
                    
                    # Combine fundamental (news) + technical (ICT) + macro edge using a scoring system
                    macro_score = 1 if macro_outlook == "BULLISH" else (-1 if macro_outlook == "BEARISH" else 0)
                    news_score = 1 if news_sentiment == "BULLISH" else (-1 if news_sentiment == "BEARISH" else 0)
                    ict_score = 1 if ict_trend == "BULLISH" else (-1 if ict_trend == "BEARISH" else 0)
                    
                    total_score = macro_score + news_score + ict_score
                    
                    if total_score > 0:
                        edge = "BULLISH"
                    elif total_score < 0:
                        edge = "BEARISH"
                    else:
                        edge = "NEUTRAL"
                    
                    if edge == "NEUTRAL":
                        logger.info(f"Conflicting or neutral signals for {symbol} (Score: {total_score}).")
                        
                    # Re-evaluate existing positions
                    if symbol in state["active_symbols"]:
                        pos_direction = self.get_position_direction(symbol, state["raw_positions"])
                        
                        # If the edge has flipped completely against our position, close it!
                        if (pos_direction == "BULLISH" and edge == "BEARISH") or (pos_direction == "BEARISH" and edge == "BULLISH"):
                            logger.warning(f"🚨 EDGE FLIPPED for {symbol}! Position is {pos_direction} but Edge is {edge}. Bailing out.")
                            await self.close_underlying_positions(symbol, state["raw_positions"])
                        else:
                            logger.info(f"Edge still supports or is neutral for {symbol}. Holding.")
                        continue # Already hold it, don't open new ones
                        
                    # Skip new trades if edge is neutral
                    if edge == "NEUTRAL":
                        continue
                    
                    chain = await self.options_service.get_option_chain(symbol)
                    
                    # Generate candidates based on combined edge
                    candidates = []
                    if edge == "BULLISH":
                        candidates = self.strategy_engine.find_bull_call_spreads(chain)
                    elif edge == "BEARISH":
                        candidates = self.strategy_engine.find_bear_put_spreads(chain)
                    
                    if not candidates:
                        logger.info(f"No viable candidates for {symbol}")
                        continue
                        
                    # Score & Rank
                    ranked = self.scorer.rank(candidates)
                    top_candidate = ranked[0]
                    
                    if top_candidate.confidence < 50:
                        logger.info(f"Top candidate for {symbol} has low confidence ({top_candidate.confidence:.1f}). Skipping.")
                        continue
                        
                    # Pre-flight Risk Check
                    if not self.risk_engine.approve_trade(top_candidate, current_total_risk=state["current_exposure"]):
                        logger.info(f"Top candidate for {symbol} rejected by RiskEngine.")
                        continue
                        
                    # AI Decision
                    logger.info(f"Asking AI to review {top_candidate.strategy} on {symbol}...")
                    decision = await self.ai_agent.evaluate_candidate(top_candidate)
                    
                    if decision.approved:
                        logger.info(f"AI APPROVED trade! Reason: {decision.reasoning}")
                        if settings.trading_enabled:
                            orders = await self.execution.execute_trade(
                                top_candidate, 
                                current_total_risk=state["current_exposure"]
                            )
                            logger.info(f"Orders submitted: {orders}")
                        else:
                            logger.info(f"TRADING_ENABLED is false. Simulating execution for {symbol}...")
                    else:
                        logger.info(f"AI REJECTED trade. Reason: {decision.reasoning}")
                    
                except Exception as e:
                    logger.error(f"Error processing {symbol}: {str(e)}")
                    
        except Exception as e:
            logger.error(f"Error in trading step: {str(e)}")

    async def run(self, interval_seconds=60):
        logger.info("Starting Autonomous Trading Loop")
        while True:
            try:
                # Check if market is open
                clock_response = await self.alpaca_client.client.get("https://paper-api.alpaca.markets/v2/clock")
                is_open = clock_response.json().get("is_open", False)
                
                if not is_open:
                    logger.info("Market is currently closed. Sleeping for 5 minutes...")
                    await asyncio.sleep(300)
                    continue
                    
                await self.step()
            except Exception as e:
                logger.error(f"Error in main run loop: {e}")
                
            logger.info(f"Sleeping for {interval_seconds} seconds...")
            await asyncio.sleep(interval_seconds)

async def start_dummy_server():
    """Starts a dummy web server so cloud platforms (like Render Web Services) don't crash waiting for a port binding."""
    import os
    import uvicorn
    from fastapi import FastAPI
    
    app = FastAPI()
    
    @app.get("/")
    @app.get("/health")
    async def health_check():
        return {"status": "Trading Bot is running!"}
        
    port = int(os.environ.get("PORT", 8080))
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")
    server = uvicorn.Server(config)
    
    # Run the uvicorn server in the asyncio event loop
    logger.info(f"Dummy health-check server starting on port {port}")
    await server.serve()

async def main():
    # Start the dummy web server concurrently with the trading loop
    loop = TradingLoop()
    await asyncio.gather(
        start_dummy_server(),
        loop.run()
    )

if __name__ == "__main__":
    asyncio.run(main())
