from fastapi import FastAPI

from app.api.options import router as options_router


app = FastAPI(
    title="Autonomous Options Trading Agent",
    description=(
        "AI-powered options research, strategy, risk analysis "
        "and paper-trading platform."
    ),
    version="0.1.0",
)


@app.get("/api/v1/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "options-agent",
        "version": "0.1.0",
    }


app.include_router(options_router)