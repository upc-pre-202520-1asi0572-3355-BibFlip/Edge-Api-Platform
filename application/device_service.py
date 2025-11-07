from typing import List, Optional
from datetime import datetime, timedelta, UTC
from domain.model.device import Device, DeviceId, DeviceType, DeviceStatus, Location
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
        """Register a new IoT device and sync with backend"""
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

        # Save in Edge API (in-memory)
        saved_device = await self._repository.save(device)

        # Sync with backend asynchronously (non-blocking)
        if self._backend_enabled:
            asyncio.create_task(self._sync_device_registration(
                device_id, device_type, branch_id, zone, position
            ))

        return saved_device

    async def _sync_device_registration(
            self,
            device_id: str,
            device_type: str,
            branch_id: str,
            zone: str,
            position: str
    ):
        """Sync device registration with backend (background task)"""
        try:
            async with BackendClient(self._backend_url) as client:
                await client.register_device_in_backend(
                    device_id, device_type, branch_id, zone, position
                )
        except Exception as e:
            logger.error(f"Failed to sync device registration to backend: {str(e)}")

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
            asyncio.create_task(self._sync_cubicle_status(
                device_id,
                saved_device.status.value
            ))

        return saved_device

    async def _sync_cubicle_status(
            self,
            device_id: str,
            status: str
    ):
        """Sync cubicle status with backend (background task)"""
        try:
            # Extract cubicle_id from device_id
            # Ejemplo: "ESP32_CUBICLE_1" -> cubicle_id = 1
            cubicle_id = self._extract_cubicle_id(device_id)

            if cubicle_id is None:
                logger.warning(f"Could not extract cubicle_id from device_id: {device_id}")
                return

            # Map Edge API status to Backend status
            backend_status = self._map_status_to_backend(status)

            async with BackendClient(self._backend_url) as client:
                success = await client.update_cubicle_status(cubicle_id, backend_status)
                if success:
                    logger.info(f"Successfully synced status for cubicle {cubicle_id} to backend")
                else:
                    logger.warning(f"Failed to sync status for cubicle {cubicle_id} to backend")
        except Exception as e:
            logger.error(f"Error syncing status to backend: {str(e)}")

    @staticmethod
    def _extract_cubicle_id(device_id: str) -> Optional[int]:
        """
        Extract cubicle ID from device ID.
        """
        try:
            # Try to extract number from string
            import re
            match = re.search(r'(\d+)', device_id)
            if match:
                return int(match.group(1))
            return None
        except Exception as e:
            logger.error(f"Error extracting cubicle_id: {str(e)}")
            return None

    @staticmethod
    def _map_status_to_backend(edge_status: str) -> str:
        """
        Map Edge API status to Backend status.
        Edge API: available, occupied, offline, error
        Backend: AVAILABLE, OCCUPIED, OFFLINE, ERROR
        """
        status_map = {
            "available": "AVAILABLE",
            "occupied": "OCCUPIED",
            "offline": "OFFLINE",
            "error": "ERROR"
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