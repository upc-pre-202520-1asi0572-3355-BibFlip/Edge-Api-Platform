from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional

from domain.model.valueobjects.device_status import DeviceStatus
from domain.model.valueobjects.device_type import DeviceType

# Zona horaria de Lima/Perú (UTC-5)
LIMA_TZ = timezone(timedelta(hours=-5))

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
            object.__setattr__(self, 'timestamp', datetime.now(LIMA_TZ))


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
    cubicle_id: Optional[int] = None

    def __post_init__(self):
        if self.last_update is None:
            self.last_update = datetime.now(LIMA_TZ)

    def update_reading(self, pressure: float, threshold: float = 30.0):
        """Update device reading and determine status"""
        self.last_reading = PressureReading(value=pressure)
        self.last_update = datetime.now(LIMA_TZ)

        # Determine status based on pressure threshold
        if pressure >= threshold:
            self.status = DeviceStatus.OCCUPIED
        else:
            self.status = DeviceStatus.AVAILABLE

    def mark_offline(self):
        """Mark device as offline"""
        self.status = DeviceStatus.OFFLINE
        self.last_update = datetime.now(LIMA_TZ)

    def mark_error(self):
        """Mark device with error status"""
        self.status = DeviceStatus.ERROR
        self.last_update = datetime.now(LIMA_TZ)

    def assign_to_cubicle(self, cubicle_id: int):
        """Assign device to a cubicle"""
        if cubicle_id <= 0:
            raise ValueError("Cubicle ID must be positive")
        self.cubicle_id = cubicle_id
        self.last_update = datetime.now(LIMA_TZ)

    def unassign_from_cubicle(self):
        """Remove cubicle assignment"""
        self.cubicle_id = None
        self.last_update = datetime.now(LIMA_TZ)

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
            "cubicle_id": self.cubicle_id,  # ← AGREGAR ESTA LÍNEA
            "last_reading": {
                "value": self.last_reading.value,
                "unit": self.last_reading.unit,
                "timestamp": self.last_reading.timestamp.isoformat()
            } if self.last_reading else None,
            "last_update": self.last_update.isoformat()
        }