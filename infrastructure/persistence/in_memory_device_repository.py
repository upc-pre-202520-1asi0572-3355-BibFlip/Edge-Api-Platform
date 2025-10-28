from typing import Dict, List, Optional
from domain.model.device import Device, DeviceId, DeviceStatus
from domain.repository.device_repository import DeviceRepository


class InMemoryDeviceRepository(DeviceRepository):
    """In-memory implementation for Edge API (lightweight)"""

    def __init__(self):
        self._devices: Dict[str, Device] = {}

    async def save(self, device: Device) -> Device:
        """Save or update a device"""
        self._devices[device.id.value] = device
        return device

    async def find_by_id(self, device_id: DeviceId) -> Optional[Device]:
        """Find device by ID"""
        return self._devices.get(device_id.value)

    async def find_all(self) -> List[Device]:
        """Find all devices"""
        return list(self._devices.values())

    async def find_by_branch(self, branch_id: str) -> List[Device]:
        """Find all devices in a branch"""
        return [
            device for device in self._devices.values()
            if device.location.branch_id == branch_id
        ]

    async def find_by_status(self, status: DeviceStatus) -> List[Device]:
        """Find devices by status"""
        return [
            device for device in self._devices.values()
            if device.status == status
        ]

    async def delete(self, device_id: DeviceId) -> bool:
        """Delete a device"""
        if device_id.value in self._devices:
            del self._devices[device_id.value]
            return True
        return False

    async def exists(self, device_id: DeviceId) -> bool:
        """Check if device exists"""
        return device_id.value in self._devices