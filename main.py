from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from interface.api.device_controller import router as device_router, set_backend_url
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Backend configuration
BACKEND_URL = os.environ.get(
    "BACKEND_URL",
    "https://bibflip-backend.azurewebsites.net"  # Tu backend Spring Boot
)

# Create FastAPI app
app = FastAPI(
    title="BibFlip IoT Edge API",
    description="Edge API for IoT chair sensors with backend synchronization",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set backend URL for device controller
set_backend_url(BACKEND_URL)
logger.info(f"Backend URL configured: {BACKEND_URL}")

# Include routers
app.include_router(device_router)


@app.get("/")
async def root():
    return {
        "service": "BibFlip IoT Edge API",
        "version": "2.0.0",
        "status": "running",
        "backend": BACKEND_URL,
        "docs": "/api/docs"
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "edge_api": "online",
        "backend_url": BACKEND_URL
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))

    logger.info("=" * 60)
    logger.info("BibFlip IoT Edge API Starting")
    logger.info("=" * 60)
    logger.info(f"Port: {port}")
    logger.info(f"Backend: {BACKEND_URL}")
    logger.info("=" * 60)

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        log_level="info"
    )