from abc import ABC, abstractmethod
from typing import List, Optional
from domain.model.aggregates.device import Device, DeviceId, DeviceStatus


class DeviceRepository(ABC):
    """Repository interface for Device aggregate"""

    @abstractmethod
    async def save(self, device: Device) -> Device:
        """Save or update a device"""
        pass

    @abstractmethod
    async def find_by_id(self, device_id: DeviceId) -> Optional[Device]:
        """Find device by ID"""
        pass

    @abstractmethod
    async def find_all(self) -> List[Device]:
        """Find all devices"""
        pass

    @abstractmethod
    async def find_by_branch(self, branch_id: str) -> List[Device]:
        """Find all devices in a branch"""
        pass

    @abstractmethod
    async def find_by_status(self, status: DeviceStatus) -> List[Device]:
        """Find devices by status"""
        pass

    @abstractmethod
    async def delete(self, device_id: DeviceId) -> bool:
        """Delete a device"""
        pass

    @abstractmethod
    async def exists(self, device_id: DeviceId) -> bool:
        """Check if device exists"""
        pass

    @abstractmethod
    async def find_by_cubicle_id(self, cubicle_id: int) -> Optional[Device]:
        """Find device assigned to a cubicle"""
        pass