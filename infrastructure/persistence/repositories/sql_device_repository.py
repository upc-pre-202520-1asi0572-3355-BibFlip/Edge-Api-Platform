from typing import List, Optional
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, UTC

from domain.model.aggregates.device import Device, DeviceId, DeviceType, DeviceStatus, Location, PressureReading
from domain.repository.device_repository import DeviceRepository
from infrastructure.persistence.models.device_model import DeviceModel, DeviceStatusEnum, DeviceTypeEnum


def _model_to_entity(model: DeviceModel) -> Device:
    """Convert SQLAlchemy model to domain entity"""
    last_reading = None
    if model.last_pressure is not None:
        last_reading = PressureReading(
            value=model.last_pressure,
            unit=model.last_pressure_unit,
            timestamp=model.last_pressure_timestamp
        )

    device = Device(
        id=DeviceId(model.id),
        type=DeviceType(model.type.value),
        status=DeviceStatus(model.status.value),
        location=Location(
            branch_id=model.branch_id,
            zone=model.zone,
            position=model.position
        ),
        last_reading=last_reading,
        last_update=model.last_update,
        cubicle_id=model.cubicle_id
    )

    return device


class SQLAlchemyDeviceRepository(DeviceRepository):
    """SQLAlchemy implementation for Device repository with PostgreSQL"""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def save(self, device: Device) -> Device:
        """Save or update a device"""
        result = await self._session.execute(
            select(DeviceModel).where(DeviceModel.id == device.id.value)
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing
            existing.type = DeviceTypeEnum(device.type.value)
            existing.status = DeviceStatusEnum(device.status.value)
            existing.branch_id = device.location.branch_id
            existing.zone = device.location.zone
            existing.position = device.location.position
            existing.cubicle_id = device.cubicle_id

            if device.last_reading:
                existing.last_pressure = device.last_reading.value
                existing.last_pressure_unit = device.last_reading.unit
                existing.last_pressure_timestamp = device.last_reading.timestamp

            existing.last_update = device.last_update
        else:
            # Create new
            device_model = DeviceModel(
                id=device.id.value,
                type=DeviceTypeEnum(device.type.value),
                status=DeviceStatusEnum(device.status.value),
                branch_id=device.location.branch_id,
                zone=device.location.zone,
                position=device.location.position,
                cubicle_id=device.cubicle_id,
                last_update=device.last_update,
                created_at=datetime.now(UTC)
            )

            if device.last_reading:
                device_model.last_pressure = device.last_reading.value
                device_model.last_pressure_unit = device.last_reading.unit
                device_model.last_pressure_timestamp = device.last_reading.timestamp

            self._session.add(device_model)

        await self._session.commit()
        return device

    async def find_by_id(self, device_id: DeviceId) -> Optional[Device]:
        """Find device by ID"""
        result = await self._session.execute(
            select(DeviceModel).where(DeviceModel.id == device_id.value)
        )
        device_model = result.scalar_one_or_none()

        if not device_model:
            return None

        return _model_to_entity(device_model)

    async def find_all(self) -> List[Device]:
        """Find all devices"""
        result = await self._session.execute(select(DeviceModel))
        device_models = result.scalars().all()

        return [_model_to_entity(dm) for dm in device_models]

    async def find_by_branch(self, branch_id: str) -> List[Device]:
        """Find all devices in a branch"""
        result = await self._session.execute(
            select(DeviceModel).where(DeviceModel.branch_id == branch_id)
        )
        device_models = result.scalars().all()

        return [_model_to_entity(dm) for dm in device_models]

    async def find_by_status(self, status: DeviceStatus) -> List[Device]:
        """Find devices by status"""
        result = await self._session.execute(
            select(DeviceModel).where(DeviceModel.status == DeviceStatusEnum(status.value))
        )
        device_models = result.scalars().all()

        return [_model_to_entity(dm) for dm in device_models]

    async def find_by_cubicle_id(self, cubicle_id: int) -> Optional[Device]:
        """Find device assigned to a cubicle"""
        result = await self._session.execute(
            select(DeviceModel).where(DeviceModel.cubicle_id == cubicle_id)
        )
        device_model = result.scalar_one_or_none()

        if not device_model:
            return None

        return _model_to_entity(device_model)

    async def delete(self, device_id: DeviceId) -> bool:
        """Delete a device"""
        result = await self._session.execute(
            delete(DeviceModel).where(DeviceModel.id == device_id.value)
        )
        await self._session.commit()
        return result.rowcount > 0

    async def exists(self, device_id: DeviceId) -> bool:
        """Check if device exists"""
        result = await self._session.execute(
            select(DeviceModel.id).where(DeviceModel.id == device_id.value)
        )
        return result.scalar_one_or_none() is not None

