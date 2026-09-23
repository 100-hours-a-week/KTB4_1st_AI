from fastapi import FastAPI
from fastapi.responses import JSONResponse

import logging

from core.config import settings
from features.moderation.router import router as moderation_router
from features.price.router import router as price_router
from features.vision.router import router as vision_router

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="AI Server")

app.include_router(vision_router)
app.include_router(moderation_router)

app.include_router(price_router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/health/liveness")
async def liveness():
    return {"status": "ok"}


@app.get("/health/readiness")
async def readiness():
    if not settings.anthropic_api_key:
        return JSONResponse(status_code=503, content={"status": "not_ready"})
    return {"status": "ready"}
