from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from typing import List, Optional
from application.device_service import DeviceService
from domain.repository.device_repository import DeviceRepository
from infrastructure.persistence.in_memory_device_repository import InMemoryDeviceRepository


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


class DeviceResponse(BaseModel):
    id: str
    type: str
    status: str
    location: dict
    last_reading: Optional[dict]
    last_update: str


# Dependency Injection
_repository: DeviceRepository = InMemoryDeviceRepository()
_service: DeviceService = DeviceService(_repository)


def get_device_service() -> DeviceService:
    return _service


# Router
router = APIRouter(prefix="/api/v1/devices", tags=["IoT Device Monitoring"])


# ==================== CRITICAL: POST must be BEFORE GET / ====================
# FastAPI matches routes in order. If GET / comes first, it catches everything

@router.post("/", response_model=DeviceResponse, status_code=201)
async def register_device(
        request: RegisterDeviceRequest,
        service: DeviceService = Depends(get_device_service)
):
    """Register a new IoT device in the system"""
    try:
        device = await service.register_device(
            device_id=request.device_id,
            device_type=request.device_type,
            branch_id=request.branch_id,
            zone=request.zone,
            position=request.position
        )
        return DeviceResponse(**device.to_dict())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== Specific routes BEFORE generic ones ====================

@router.get("/status/available", response_model=List[DeviceResponse])
async def get_available_devices(
        branch_id: Optional[str] = Query(None, description="Filter by branch ID"),
        service: DeviceService = Depends(get_device_service)
):
    """Get all available devices"""
    devices = await service.get_available_devices(branch_id)
    return [DeviceResponse(**d.to_dict()) for d in devices]


@router.get("/status/occupied", response_model=List[DeviceResponse])
async def get_occupied_devices(
        branch_id: Optional[str] = Query(None, description="Filter by branch ID"),
        service: DeviceService = Depends(get_device_service)
):
    """Get all occupied devices"""
    devices = await service.get_occupied_devices(branch_id)
    return [DeviceResponse(**d.to_dict()) for d in devices]


@router.post("/maintenance/check-offline", response_model=List[DeviceResponse])
async def check_offline_devices(
        timeout_minutes: int = Query(5, ge=1, description="Minutes without update to consider offline"),
        service: DeviceService = Depends(get_device_service)
):
    """Check and mark devices as offline if no recent updates"""
    devices = await service.check_offline_devices(timeout_minutes)
    return [DeviceResponse(**d.to_dict()) for d in devices]


# ==================== Path parameter routes ====================

@router.post("/{device_id}/readings", response_model=DeviceResponse)
async def update_device_reading(
        device_id: str,
        request: UpdateReadingRequest,
        service: DeviceService = Depends(get_device_service)
):
    """Update device reading (used by ESP32)"""
    try:
        device = await service.update_device_reading(
            device_id=device_id,
            pressure=request.pressure,
            threshold=request.threshold
        )
        return DeviceResponse(**device.to_dict())
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{device_id}", response_model=DeviceResponse)
async def get_device(
        device_id: str,
        service: DeviceService = Depends(get_device_service)
):
    """Get device information by ID"""
    device = await service.get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
    return DeviceResponse(**device.to_dict())


@router.delete("/{device_id}", status_code=204)
async def delete_device(
        device_id: str,
        service: DeviceService = Depends(get_device_service)
):
    """Delete a device from the system"""
    deleted = await service.delete_device(device_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
    return None


# ==================== Generic list route LAST ====================

@router.get("/", response_model=List[DeviceResponse])
async def get_all_devices(
        branch_id: Optional[str] = Query(None, description="Filter by branch ID"),
        service: DeviceService = Depends(get_device_service)
):
    """Get all devices or filter by branch"""
    if branch_id:
        devices = await service.get_devices_by_branch(branch_id)
    else:
        devices = await service.get_all_devices()

    return [DeviceResponse(**d.to_dict()) for d in devices]