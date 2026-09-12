from fastapi import APIRouter
from app.api.v1.endpoints import camera, health, video

api_router = APIRouter()

# Health route
api_router.include_router(health.router, tags=["Health"])

# Video and camera input routes
api_router.include_router(video.router, prefix="/input", tags=["Video Input"])
api_router.include_router(camera.router, prefix="/input", tags=["Camera Input"])
