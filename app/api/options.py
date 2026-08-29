from fastapi import APIRouter, HTTPException

from app.services.options_service import OptionsService


router = APIRouter(
    prefix="/api/v1/options",
    tags=["Options"],
)


@router.get("/{symbol}")
async def get_option_chain(symbol: str):
    service = OptionsService()

    try:
        return await service.get_option_chain(symbol)

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Unable to retrieve option chain: {str(exc)}",
        )

    finally:
        await service.close()