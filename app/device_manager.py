from typing import Dict, Optional
from datetime import datetime
import asyncio
from dataclasses import dataclass
from enum import Enum

class DeviceType(Enum):
    HELMET = "helmet"
    BIKE = "bike"

class DeviceStatus(Enum):
    UNKNOWN = "unknown"
    SAFE = "safe"
    DRUNKEN = "drunken"
    OVERRIDE = "override"

@dataclass
class Device:
    uuid: str
    type: DeviceType
    status: DeviceStatus
    last_seen: datetime
    api_token: Optional[str] = None

class DeviceManager:
    def __init__(self):
        self.devices: Dict[str, Device] = {}
        self.status_lock = asyncio.Lock()
    
    async def register_device(self, uuid: str, device_type: DeviceType, api_token: Optional[str] = None) -> Device:
        """Register a new device or update existing one"""
        async with self.status_lock:
            if uuid not in self.devices:
                self.devices[uuid] = Device(
                    uuid=uuid,
                    type=device_type,
                    status=DeviceStatus.UNKNOWN,
                    last_seen=datetime.now(),
                    api_token=api_token
                )
            else:
                self.devices[uuid].last_seen = datetime.now()
                if api_token:
                    self.devices[uuid].api_token = api_token
            return self.devices[uuid]
    
    async def update_status(self, uuid: str, status: DeviceStatus) -> bool:
        """Update device status"""
        async with self.status_lock:
            if uuid in self.devices:
                self.devices[uuid].status = status
                self.devices[uuid].last_seen = datetime.now()
                return True
            return False
    
    async def get_status(self, uuid: str) -> Optional[DeviceStatus]:
        """Get device status"""
        async with self.status_lock:
            if uuid in self.devices:
                return self.devices[uuid].status
            return None
    
    async def get_helmet_status(self) -> DeviceStatus:
        """Get status of the first helmet device found"""
        async with self.status_lock:
            for device in self.devices.values():
                if device.type == DeviceType.HELMET:
                    return device.status
            return DeviceStatus.UNKNOWN
    
    async def verify_token(self, uuid: str, token: str) -> bool:
        """Verify device API token"""
        async with self.status_lock:
            if uuid in self.devices:
                return self.devices[uuid].api_token == token
            return False

# Global device manager instance
device_manager = DeviceManager() 