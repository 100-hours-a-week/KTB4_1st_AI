from fastapi import FastAPI

from features.moderation.router import router as moderation_router
from features.vision.router import router as vision_router

app = FastAPI(title="AI Server")

app.include_router(vision_router)
app.include_router(moderation_router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
