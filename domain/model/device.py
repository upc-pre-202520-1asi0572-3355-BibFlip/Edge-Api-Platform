from dataclasses import dataclass
from datetime import datetime, UTC
from enum import Enum
from typing import Optional


class DeviceStatus(Enum):
    AVAILABLE = "available"
    OCCUPIED = "occupied"
    OFFLINE = "offline"
    ERROR = "error"


class DeviceType(Enum):
    CHAIR_SENSOR = "chair_sensor"
    TABLE_SENSOR = "table_sensor"
    ENVIRONMENTAL = "environmental"


@dataclass(frozen=True)
class DeviceId:
    value: str

    def __post_init__(self):
        if not self.value or len(self.value) < 3:
            raise ValueError("DeviceId must have at least 3 characters")


@dataclass(frozen=True)
class PressureReading:
    value: float
    unit: str = "%"
    timestamp: datetime = None

    def __post_init__(self):
        if self.value < 0 or self.value > 100:
            raise ValueError("Pressure must be between 0 and 100")
        if self.timestamp is None:
            object.__setattr__(self, 'timestamp', datetime.now(UTC))


@dataclass(frozen=True)
class Location:
    branch_id: str
    zone: str
    position: str

    def __post_init__(self):
        if not all([self.branch_id, self.zone, self.position]):
            raise ValueError("All location fields are required")


@dataclass
class Device:
    id: DeviceId
    type: DeviceType
    status: DeviceStatus
    location: Location
    last_reading: Optional[PressureReading] = None
    last_update: datetime = None

    def __post_init__(self):
        if self.last_update is None:
            self.last_update = datetime.now(UTC)

    def update_reading(self, pressure: float, threshold: float = 30.0):
        """Update device reading and determine status"""
        self.last_reading = PressureReading(value=pressure)
        self.last_update = datetime.now(UTC)

        # Determine status based on pressure threshold
        if pressure >= threshold:
            self.status = DeviceStatus.OCCUPIED
        else:
            self.status = DeviceStatus.AVAILABLE

    def mark_offline(self):
        """Mark device as offline"""
        self.status = DeviceStatus.OFFLINE
        self.last_update = datetime.now(UTC)

    def mark_error(self):
        """Mark device with error status"""
        self.status = DeviceStatus.ERROR
        self.last_update = datetime.now(UTC)

    def to_dict(self):
        return {
            "id": self.id.value,
            "type": self.type.value,
            "status": self.status.value,
            "location": {
                "branch_id": self.location.branch_id,
                "zone": self.location.zone,
                "position": self.location.position
            },
            "last_reading": {
                "value": self.last_reading.value,
                "unit": self.last_reading.unit,
                "timestamp": self.last_reading.timestamp.isoformat()
            } if self.last_reading else None,
            "last_update": self.last_update.isoformat()
        }