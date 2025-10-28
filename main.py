from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from interface.api.device_controller import router as device_router
import os

# Create FastAPI app
app = FastAPI(
    title="IoT Device Monitoring Edge API",
    description="Edge API for monitoring IoT devices (chairs, tables sensors) using DDD",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(device_router)


@app.get("/")
async def root():
    return {
        "service": "IoT Device Monitoring Edge API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/api/docs"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))  # Puerto dinámico para Render
    uvicorn.run(app, host="0.0.0.0", port=port)