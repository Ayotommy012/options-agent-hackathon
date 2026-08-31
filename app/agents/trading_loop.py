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
            
    async def get_technical_trend(self, symbol: str) -> str:
        """Fetch historical bars from Alpaca to determine structural technical trend (50-day SMA)."""
        try:
            from datetime import datetime, timedelta, timezone
            start_date = (datetime.now(timezone.utc) - timedelta(days=90)).strftime('%Y-%m-%dT%H:%M:%SZ')
            url = f"https://data.alpaca.markets/v2/stocks/bars?symbols={symbol}&timeframe=1Day&start={start_date}&limit=100"
            response = await self.alpaca_client.client.get(url)
            bars = response.json().get("bars", {}).get(symbol, [])
            
            if len(bars) < 20:
                logger.warning(f"Not enough bar data for {symbol} to calculate MA.")
                return "NEUTRAL"
                
            # Calculate 50-day Simple Moving Average (or as many days as we have up to 50)
            closes = [b.get("c", 0.0) for b in bars][-50:]
            sma = sum(closes) / len(closes)
            current_price = closes[-1]
            
            # Require 1% buffer to avoid chopping back and forth
            if current_price > sma * 1.01:
                return "BULLISH"
            elif current_price < sma * 0.99:
                return "BEARISH"
            else:
                return "NEUTRAL"
        except Exception as e:
            logger.error(f"Error fetching technical trend for {symbol}: {e}")
            return "NEUTRAL"

    async def step(self):
        logger.info("--- Starting Trading Loop Step ---")
        
        try:
            # 1. Get State
            state = await self.portfolio_service.get_portfolio_state()
            
            # Update RiskEngine dynamically with live equity
            self.risk_engine.account_size = state["equity"]
            self.risk_engine.max_risk_per_trade = state["equity"] * 0.02
            self.risk_engine.max_total_risk = state["equity"] * 0.10
            
            # 2. Position Monitoring & P&L
            await self.track_pnl_and_monitor_positions(state)
            
            # 3. Discover new trades
            for symbol in self.symbols_to_monitor:
                if symbol in state["active_symbols"]:
                    logger.info(f"Already have exposure to {symbol}. Skipping.")
                    continue
                    
                logger.info(f"Analyzing {symbol} for opportunities...")
                
                try:
                    news_sentiment = await self.get_sentiment(symbol)
                    tech_trend = await self.get_technical_trend(symbol)
                    logger.info(f"Signals for {symbol} -> News: {news_sentiment} | Technical (50-SMA): {tech_trend}")
                    
                    # Combine fundamental (news) + technical (MA) edge using a scoring system
                    # This allows the bot to trade on just news, just MA, or both, while avoiding conflicting trades.
                    news_score = 1 if news_sentiment == "BULLISH" else (-1 if news_sentiment == "BEARISH" else 0)
                    tech_score = 1 if tech_trend == "BULLISH" else (-1 if tech_trend == "BEARISH" else 0)
                    
                    total_score = news_score + tech_score
                    
                    if total_score > 0:
                        edge = "BULLISH"
                    elif total_score < 0:
                        edge = "BEARISH"
                    else:
                        logger.info(f"Conflicting or neutral signals for {symbol} (Score: {total_score}), sitting out.")
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
            
if __name__ == "__main__":
    loop = TradingLoop()
    asyncio.run(loop.run())
