import enum

from sqlalchemy import Column, String, Integer, Float, DateTime, Enum as SQLEnum
from sqlalchemy.sql import func
from datetime import datetime, timezone, timedelta
from infrastructure.persistence.configuration.database_configuration import Base


LIMA_TZ = timezone(timedelta(hours=-5))

def lima_now():
    return datetime.now(timezone.utc).astimezone(LIMA_TZ)


class DeviceStatusEnum(str, enum.Enum):
    AVAILABLE = "available"
    OCCUPIED = "occupied"
    OFFLINE = "offline"
    ERROR = "error"


class DeviceTypeEnum(str, enum.Enum):
    CHAIR_SENSOR = "chair_sensor"
    TABLE_SENSOR = "table_sensor"
    ENVIRONMENTAL = "environmental"


class DeviceModel(Base):
    """SQLAlchemy model for Device persistence"""

    __tablename__ = "devices"

    id = Column(String(100), primary_key=True, index=True)
    type = Column(SQLEnum(DeviceTypeEnum), nullable=False)
    status = Column(SQLEnum(DeviceStatusEnum), nullable=False, default=DeviceStatusEnum.OFFLINE)

    # Location
    branch_id = Column(String(100), nullable=False)
    zone = Column(String(100), nullable=False)
    position = Column(String(100), nullable=False)

    # Cubicle ID (nullable - can be assigned later)
    cubicle_id = Column(Integer, nullable=True, index=True)

    # Last reading
    last_pressure = Column(Float, nullable=True)
    last_pressure_unit = Column(String(10), default="%")
    last_pressure_timestamp = Column(DateTime, nullable=True)

    # Timestamps
    last_update = Column(DateTime(timezone=True), nullable=False, default=lima_now, onupdate=lima_now)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lima_now)

    def __repr__(self):
        return f"<Device(id='{self.id}', type='{self.type}', status='{self.status}', cubicle_id={self.cubicle_id})>"