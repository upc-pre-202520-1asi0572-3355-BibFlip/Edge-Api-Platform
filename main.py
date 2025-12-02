import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html

from infrastructure.persistence.configuration.database_configuration import init_db, close_db
from interface.api.device_controller import router as device_router, set_backend_url

# Configurar el event loop correcto ANTES de cualquier import asíncrono
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    logging.info("Windows detected: Using WindowsSelectorEventLoopPolicy for async operations")


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Backend configuration
BACKEND_URL = os.environ.get(
    "BACKEND_URL",
    "https://bibflip-api-platform.azurewebsites.net"
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Application lifecycle: startup and shutdown"""
    logger.info("=" * 60)
    logger.info("Initializing database...")
    await init_db()
    logger.info("Database initialized successfully")
    logger.info("=" * 60)

    yield

    logger.info("Closing database...")
    await close_db()
    logger.info("Database closed")


# Create FastAPI app - DESHABILITAR docs_url y redoc_url por defecto
app = FastAPI(
    title="BibFlip IoT Edge API",
    description="Edge API for IoT chair sensors with PostgreSQL persistence",
    version="2.0.0",
    docs_url=None,  # ⬅️ Deshabilitar
    redoc_url=None,  # ⬅️ Deshabilitar
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware, # type: ignore
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


@app.get("/api/docs", include_in_schema=False)
async def custom_swagger_ui():
    """Custom Swagger UI with reliable CDN"""
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title=f"BibFlip - Swagger UI",
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.11.0/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.11.0/swagger-ui.css",
    )


@app.get("/api/redoc", include_in_schema=False)
async def custom_redoc():
    """Custom ReDoc with reliable CDN"""
    return get_redoc_html(
        openapi_url="/openapi.json",
        title=f"BibFlip - ReDoc",
        redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@latest/bundles/redoc.standalone.js",
    )


@app.get("/")
async def root():
    return {
        "service": "BibFlip IoT Edge API",
        "version": "2.0.0",
        "status": "running",
        "backend": BACKEND_URL,
        "docs": "/api/docs",
        "redoc": "/api/redoc"
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