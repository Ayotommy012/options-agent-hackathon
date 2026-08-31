import json
import logging
from openai import AsyncOpenAI
from pydantic import BaseModel
from app.schemas.trading_strategy import TradeCandidate
from app.core.config import settings

logger = logging.getLogger(__name__)

class AgentDecision(BaseModel):
    approved: bool
    confidence_score: float
    reasoning: str


class DecisionAgent:
    def __init__(self, model_name: str = "nvidia/nemotron-3.5-lightning:free"):
        # We will use OpenRouter since it is free and OpenAI-compatible
        # If openrouter key is not set, we gracefully fallback or fail
        self.model_name = model_name
        self.api_url = "https://openrouter.ai/api/v1"
        self.client = AsyncOpenAI(
            base_url=self.api_url,
            api_key=settings.openrouter_api_key or "DUMMY",
        )

    async def evaluate_candidate(self, candidate: TradeCandidate, market_context: str = "") -> AgentDecision:
        system_prompt = (
            "You are an expert options trading AI. Your job is to evaluate proposed trade candidates. "
            "You must analyze the maximum loss, maximum profit, breakeven points, and the specific option legs involved. "
            "Reject trades with poor risk-reward ratios or illogical structures. Approve solid setups. "
            "You MUST return your response as a valid JSON object matching this schema exactly: "
            "{\"approved\": bool, \"confidence_score\": float, \"reasoning\": \"string\"}"
        )

        user_prompt = f"Trade Candidate Details:\n{candidate.model_dump_json(indent=2)}\n\n"

        if market_context:
            user_prompt += f"Market Context:\n{market_context}\n\n"

        user_prompt += "Evaluate this trade and return the JSON decision."

        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
            )
            
            content = response.choices[0].message.content
            
            # Parse the JSON returned by OpenRouter
            try:
                parsed_json = json.loads(content)
                return AgentDecision(
                    approved=bool(parsed_json.get("approved", False)),
                    confidence_score=float(parsed_json.get("confidence_score", 0.0)),
                    reasoning=str(parsed_json.get("reasoning", "No reasoning provided."))
                )
            except json.JSONDecodeError:
                return AgentDecision(
                    approved=False,
                    confidence_score=0.0,
                    reasoning=f"Failed to parse JSON from AI response: {content}"
                )
        except Exception as e:
            logger.error(f"OpenRouter API error: {e}")
            return AgentDecision(
                approved=False,
                confidence_score=0.0,
                reasoning=f"Error connecting to OpenRouter: {e}"
            )
