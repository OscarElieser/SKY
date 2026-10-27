"""Private operational report for SKY GLOBAL, attached to the existing API."""
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from .api import require_key
from neural_core.sky_global_readiness import readiness

router = APIRouter(prefix="/api/sky/global", dependencies=[Depends(require_key)])


@router.get("/readiness")
def global_readiness():
    """Measured readiness. Never turns a deployment flag into certification."""
    return JSONResponse(readiness(), headers={"Cache-Control": "no-store"})
