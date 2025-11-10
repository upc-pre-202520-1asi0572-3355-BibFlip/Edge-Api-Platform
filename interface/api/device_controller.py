from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from application.device_service import DeviceService
from infrastructure.persistence.configuration.database_configuration import get_db_session
from infrastructure.persistence.repositories.sql_device_repository import SQLAlchemyDeviceRepository
import logging

logger = logging.getLogger(__name__)


# DTOs (Data Transfer Objects)
class RegisterDeviceRequest(BaseModel):
    device_id: str = Field(..., min_length=3, description="Unique device identifier")
    device_type: str = Field(..., description="Type of device (chair_sensor, table_sensor, environmental)")
    branch_id: str = Field(..., description="Branch ID where device is located")
    zone: str = Field(..., description="Zone within the branch")
    position: str = Field(..., description="Specific position identifier")


class UpdateReadingRequest(BaseModel):
    pressure: float = Field(..., ge=0, le=100, description="Pressure reading (0-100%)")
    threshold: Optional[float] = Field(30.0, ge=0, le=100, description="Threshold for occupied status")


class AssignCubicleRequest(BaseModel):
    cubicle_id: int = Field(..., gt=0, description="Cubicle ID to assign device to")


class DeviceResponse(BaseModel):
    id: str
    type: str
    status: str
    location: dict
    cubicle_id: Optional[int]
    last_reading: Optional[dict]
    last_update: str


class HealthResponse(BaseModel):
    edge_api: str
    backend: str
    backend_reachable: bool


# Dependency Injection
_backend_url: Optional[str] = None


def set_backend_url(url: str):
    """Configure backend URL for service"""
    global _backend_url
    _backend_url = url
    logger.info(f"Backend URL configured: {url}")


async def get_device_service(
        db_session: AsyncSession = Depends(get_db_session)
) -> DeviceService:
    """Dependency to get device service with database session"""
    if _backend_url is None:
        raise HTTPException(
            status_code=500,
            detail="Device service not initialized. Backend URL not configured."
        )

    repository = SQLAlchemyDeviceRepository(db_session)
    return DeviceService(repository, backend_url=_backend_url)


# Router
router = APIRouter(prefix="/api/v1/devices", tags=["IoT Device Monitoring"])


@router.post("/register", response_model=DeviceResponse, status_code=201)
async def register_device(
        request: RegisterDeviceRequest,
        service: DeviceService = Depends(get_device_service)
):
    """
    Register a new IoT device in Edge API and sync with backend.
    Device stored in PostgreSQL.
    """
    try:
        logger.info(f"Registering device: {request.device_id}")

        device = await service.register_device(
            device_id=request.device_id,
            device_type=request.device_type,
            branch_id=request.branch_id,
            zone=request.zone,
            position=request.position
        )

        logger.info(f"Device {request.device_id} registered successfully")
        return DeviceResponse(**device.to_dict())

    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{device_id}/readings", response_model=DeviceResponse)
async def update_device_reading(
        device_id: str,
        request: UpdateReadingRequest,
        service: DeviceService = Depends(get_device_service)
):
    """
    Update device reading from ESP32.
    Data stored in PostgreSQL and synced to backend.
    """
    try:
        logger.info(f"Updating reading for device {device_id}: {request.pressure}%")

        device = await service.update_device_reading(
            device_id=device_id,
            pressure=request.pressure,
            threshold=request.threshold
        )

        logger.info(f"Reading updated for {device_id}: Status={device.status.value}")
        return DeviceResponse(**device.to_dict())

    except ValueError as e:
        logger.error(f"Device not found: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{device_id}/assign-cubicle", response_model=DeviceResponse)
async def assign_device_to_cubicle(
        device_id: str,
        request: AssignCubicleRequest,
        service: DeviceService = Depends(get_device_service)
):
    """Assign a device to a cubicle (for web app)"""
    try:
        logger.info(f"Assigning device {device_id} to cubicle {request.cubicle_id}")
        device = await service.assign_device_to_cubicle(device_id, request.cubicle_id)
        logger.info(f"Device {device_id} assigned successfully")
        return DeviceResponse(**device.to_dict())
    except ValueError as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{device_id}/unassign-cubicle", response_model=DeviceResponse)
async def unassign_device_from_cubicle(
        device_id: str,
        service: DeviceService = Depends(get_device_service)
):
    """Remove cubicle assignment from device"""
    try:
        logger.info(f"Unassigning device {device_id} from cubicle")
        device = await service.unassign_device_from_cubicle(device_id)
        logger.info(f"Device {device_id} unassigned successfully")
        return DeviceResponse(**device.to_dict())
    except ValueError as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cubicle/{cubicle_id}", response_model=DeviceResponse)
async def get_device_by_cubicle(
        cubicle_id: int,
        service: DeviceService = Depends(get_device_service)
):
    """Get device assigned to a specific cubicle"""
    device = await service.get_device_by_cubicle(cubicle_id)
    if not device:
        raise HTTPException(status_code=404, detail=f"No device assigned to cubicle {cubicle_id}")
    return DeviceResponse(**device.to_dict())


@router.get("/status/available", response_model=List[DeviceResponse])
async def get_available_devices(
        branch_id: Optional[str] = Query(None, description="Filter by branch ID"),
        service: DeviceService = Depends(get_device_service)
):
    """Get all available devices from database"""
    devices = await service.get_available_devices(branch_id)
    return [DeviceResponse(**d.to_dict()) for d in devices]


@router.get("/status/occupied", response_model=List[DeviceResponse])
async def get_occupied_devices(
        branch_id: Optional[str] = Query(None, description="Filter by branch ID"),
        service: DeviceService = Depends(get_device_service)
):
    """Get all occupied devices from database"""
    devices = await service.get_occupied_devices(branch_id)
    return [DeviceResponse(**d.to_dict()) for d in devices]


@router.get("/health/backend", response_model=HealthResponse)
async def check_backend_health(
        service: DeviceService = Depends(get_device_service)
):
    """Check if backend is reachable"""
    backend_ok = await service.check_backend_health()

    return HealthResponse(
        edge_api="online",
        backend=_backend_url or "not_configured",
        backend_reachable=backend_ok
    )


@router.post("/maintenance/check-offline", response_model=List[DeviceResponse])
async def check_offline_devices(
        timeout_minutes: int = Query(5, ge=1, description="Minutes without update to consider offline"),
        service: DeviceService = Depends(get_device_service)
):
    """Check and mark devices as offline if no recent updates"""
    devices = await service.check_offline_devices(timeout_minutes)
    return [DeviceResponse(**d.to_dict()) for d in devices]


@router.get("/{device_id}", response_model=DeviceResponse)
async def get_device(
        device_id: str,
        service: DeviceService = Depends(get_device_service)
):
    """Get device information by ID from database"""
    device = await service.get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
    return DeviceResponse(**device.to_dict())


@router.delete("/{device_id}", status_code=204)
async def delete_device(
        device_id: str,
        service: DeviceService = Depends(get_device_service)
):
    """Delete a device from database"""
    deleted = await service.delete_device(device_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
    return None


@router.get("/", response_model=List[DeviceResponse])
async def get_all_devices(
        branch_id: Optional[str] = Query(None, description="Filter by branch ID"),
        service: DeviceService = Depends(get_device_service)
):
    """Get all devices from database or filter by branch"""
    if branch_id:
        devices = await service.get_devices_by_branch(branch_id)
    else:
        devices = await service.get_all_devices()

    return [DeviceResponse(**d.to_dict()) for d in devices]