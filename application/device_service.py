from typing import List, Optional
from datetime import datetime, timedelta, UTC
from domain.model.aggregates.device import Device, DeviceId, DeviceType, DeviceStatus, Location
from domain.repository.device_repository import DeviceRepository
from infrastructure.http.backend_client import BackendClient
import logging
import asyncio

logger = logging.getLogger(__name__)


class DeviceService:
    """Application service for device operations with backend sync"""

    def __init__(
            self,
            repository: DeviceRepository,
            backend_url: Optional[str] = None
    ):
        self._repository = repository
        self._backend_url = backend_url
        self._backend_enabled = backend_url is not None

    async def register_device(
            self,
            device_id: str,
            device_type: str,
            branch_id: str,
            zone: str,
            position: str
    ) -> Device:
        """Register a new IoT device"""
        device_id_vo = DeviceId(device_id)

        # Check if device already exists
        if await self._repository.exists(device_id_vo):
            logger.info(f"Device {device_id} already exists in Edge API")
            # Return existing device
            return await self._repository.find_by_id(device_id_vo)

        device = Device(
            id=device_id_vo,
            type=DeviceType(device_type),
            status=DeviceStatus.OFFLINE,
            location=Location(
                branch_id=branch_id,
                zone=zone,
                position=position
            )
        )

        # Save in Edge API (PostgreSQL)
        saved_device = await self._repository.save(device)

        return saved_device

    async def update_device_reading(
            self,
            device_id: str,
            pressure: float,
            threshold: float = 30.0
    ) -> Device:
        """Update device reading and sync status with backend"""
        device_id_vo = DeviceId(device_id)
        device = await self._repository.find_by_id(device_id_vo)

        if not device:
            raise ValueError(f"Device {device_id} not found")

        # Update device status based on pressure
        device.update_reading(pressure, threshold)
        saved_device = await self._repository.save(device)

        # Sync status with backend asynchronously (non-blocking)
        if self._backend_enabled:
            asyncio.create_task(self._sync_cubicle_status(saved_device))

        return saved_device

    async def _sync_cubicle_status(self, device: Device):
        """Sync availability slot status with backend (background task)"""
        try:
            # CORRECCIÓN: Usar el cubicle_id asignado al dispositivo
            if device.cubicle_id is None:
                logger.warning(
                    f"Device {device.id.value} not assigned to any cubicle. "
                    f"Skipping backend sync. Use PATCH /devices/{{id}}/assign-cubicle first."
                )
                return

            cubicle_id = device.cubicle_id

            # Map Edge API status to Backend AvailabilitySlot status
            backend_status = self._map_status_to_backend(device.status.value)

            logger.info(
                f"Syncing device {device.id.value} → cubicle {cubicle_id} → status {backend_status}"
            )

            async with BackendClient(self._backend_url) as client:
                success = await client.update_availability_slot_status(cubicle_id, backend_status)
                if success:
                    logger.info(f"Successfully synced availability slot status for cubicle {cubicle_id} to backend")
                else:
                    logger.warning(f"Failed to sync availability slot status for cubicle {cubicle_id} to backend")
        except Exception as e:
            logger.error(f"Error syncing availability slot status to backend: {str(e)}")

    @staticmethod
    def _map_status_to_backend(edge_status: str) -> str:
        """
        Map Edge API status to Backend booking status.
        Edge API: available, occupied, offline, error
        Backend: AVAILABLE, RESERVED (only 2 states)

        Note: We map 'occupied' to 'RESERVED' because the backend
        doesn't have a separate OCCUPIED state yet.
        """
        status_map = {
            "available": "AVAILABLE",
            "occupied": "RESERVED",  # ← CAMBIADO: OCCUPIED → RESERVED
            "offline": "AVAILABLE",
            "error": "AVAILABLE"
        }
        return status_map.get(edge_status.lower(), "AVAILABLE")

    async def get_device(self, device_id: str) -> Optional[Device]:
        """Get device by ID"""
        return await self._repository.find_by_id(DeviceId(device_id))

    async def get_all_devices(self) -> List[Device]:
        """Get all devices"""
        return await self._repository.find_all()

    async def get_devices_by_branch(self, branch_id: str) -> List[Device]:
        """Get devices by branch"""
        return await self._repository.find_by_branch(branch_id)

    async def get_available_devices(self, branch_id: Optional[str] = None) -> List[Device]:
        """Get available devices (optionally filtered by branch)"""
        if branch_id:
            devices = await self._repository.find_by_branch(branch_id)
            return [d for d in devices if d.status == DeviceStatus.AVAILABLE]

        return await self._repository.find_by_status(DeviceStatus.AVAILABLE)

    async def get_occupied_devices(self, branch_id: Optional[str] = None) -> List[Device]:
        """Get occupied devices (optionally filtered by branch)"""
        if branch_id:
            devices = await self._repository.find_by_branch(branch_id)
            return [d for d in devices if d.status == DeviceStatus.OCCUPIED]

        return await self._repository.find_by_status(DeviceStatus.OCCUPIED)

    async def check_offline_devices(self, timeout_minutes: int = 5) -> List[Device]:
        """Check and mark devices as offline if no updates"""
        all_devices = await self._repository.find_all()
        offline_devices = []
        cutoff_time = datetime.now(UTC) - timedelta(minutes=timeout_minutes)

        for device in all_devices:
            if device.last_update < cutoff_time and device.status != DeviceStatus.OFFLINE:
                device.mark_offline()
                await self._repository.save(device)
                offline_devices.append(device)

        return offline_devices

    async def delete_device(self, device_id: str) -> bool:
        """Delete a device"""
        return await self._repository.delete(DeviceId(device_id))

    async def check_backend_health(self) -> bool:
        """Check if backend is available"""
        if not self._backend_enabled:
            return False

        try:
            async with BackendClient(self._backend_url, timeout=5.0) as client:
                return await client.health_check()
        except Exception as e:
            logger.error(f"Backend health check failed: {str(e)}")
            return False

    async def assign_device_to_cubicle(
            self,
            device_id: str,
            cubicle_id: int
    ) -> Device:
        """Assign a device to a cubicle"""
        device_id_vo = DeviceId(device_id)
        device = await self._repository.find_by_id(device_id_vo)

        if not device:
            raise ValueError(f"Device {device_id} not found")

        # Check if cubicle already has a device assigned
        existing_device = await self._repository.find_by_cubicle_id(cubicle_id)
        if existing_device and existing_device.id.value != device_id:
            raise ValueError(f"Cubicle {cubicle_id} already has device {existing_device.id.value} assigned")

        device.assign_to_cubicle(cubicle_id)
        saved_device = await self._repository.save(device)

        logger.info(f"Device {device_id} assigned to cubicle {cubicle_id}")

        return saved_device

    async def unassign_device_from_cubicle(self, device_id: str) -> Device:
        """Remove cubicle assignment from device"""
        device_id_vo = DeviceId(device_id)
        device = await self._repository.find_by_id(device_id_vo)

        if not device:
            raise ValueError(f"Device {device_id} not found")

        device.unassign_from_cubicle()
        return await self._repository.save(device)

    async def get_device_by_cubicle(self, cubicle_id: int) -> Optional[Device]:
        """Get device assigned to a specific cubicle"""
        return await self._repository.find_by_cubicle_id(cubicle_id)