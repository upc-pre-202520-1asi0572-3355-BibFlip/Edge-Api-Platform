from typing import List, Optional
from datetime import datetime, timedelta
from domain.model.device import Device, DeviceId, DeviceType, DeviceStatus, Location
from domain.repository.device_repository import DeviceRepository


class DeviceService:
    """Application service for device operations"""

    def __init__(self, repository: DeviceRepository):
        self._repository = repository

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
            raise ValueError(f"Device {device_id} already exists")

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

        return await self._repository.save(device)

    async def update_device_reading(
            self,
            device_id: str,
            pressure: float,
            threshold: float = 30.0
    ) -> Device:
        """Update device reading and status"""
        device_id_vo = DeviceId(device_id)
        device = await self._repository.find_by_id(device_id_vo)

        if not device:
            raise ValueError(f"Device {device_id} not found")

        device.update_reading(pressure, threshold)
        return await self._repository.save(device)

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
        cutoff_time = datetime.utcnow() - timedelta(minutes=timeout_minutes)

        for device in all_devices:
            if device.last_update < cutoff_time and device.status != DeviceStatus.OFFLINE:
                device.mark_offline()
                await self._repository.save(device)
                offline_devices.append(device)

        return offline_devices

    async def delete_device(self, device_id: str) -> bool:
        """Delete a device"""
        return await self._repository.delete(DeviceId(device_id))