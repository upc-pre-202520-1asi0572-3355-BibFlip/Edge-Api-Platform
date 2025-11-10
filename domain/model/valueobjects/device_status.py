from enum import Enum


class DeviceStatus(Enum):
    AVAILABLE = "available"
    OCCUPIED = "occupied"
    OFFLINE = "offline"
    ERROR = "error"