import json
import os
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import asyncio
from pathlib import Path

@dataclass
class DeviceStatus:
    uuid: str
    status: str
    timestamp: str
    alcohol_level: Optional[int] = None

@dataclass
class GPSData:
    device: str
    latitude: float
    longitude: float
    timestamp: str
    ip_location: Optional[Dict] = None

class DataManager:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        self.status_file = self.data_dir / "status.json"
        self.logs_file = self.data_dir / "logs.json"
        self.gps_file = self.data_dir / "gps.json"
        
        self._ensure_files_exist()
        self.lock = asyncio.Lock()
    
    def _ensure_files_exist(self):
        """Ensure all required JSON files exist with proper structure"""
        if not self.status_file.exists():
            self.status_file.write_text('[]')
        if not self.logs_file.exists():
            self.logs_file.write_text('[]')
        if not self.gps_file.exists():
            self.gps_file.write_text('[]')
    
    async def get_device_status(self, uuid: str) -> Optional[DeviceStatus]:
        """Get current status of a device"""
        async with self.lock:
            data = json.loads(self.status_file.read_text())
            for entry in data:
                if entry["uuid"] == uuid:
                    return DeviceStatus(**entry)
            return None
    
    async def update_device_status(self, status: DeviceStatus):
        """Update device status"""
        async with self.lock:
            data = json.loads(self.status_file.read_text())
            
            # Remove existing entry if exists
            data = [entry for entry in data if entry["uuid"] != status.uuid]
            
            # Add new entry
            data.append(vars(status))
            
            # Keep only last 1000 entries
            if len(data) > 1000:
                data = data[-1000:]
            
            self.status_file.write_text(json.dumps(data, indent=2))
    
    async def add_log(self, device: str, level: str, message: str):
        """Add a new log entry"""
        async with self.lock:
            data = json.loads(self.logs_file.read_text())
            
            log_entry = {
                "device": device,
                "level": level,
                "message": message,
                "timestamp": datetime.now().isoformat()
            }
            
            data.append(log_entry)
            
            # Keep only last 1000 entries
            if len(data) > 1000:
                data = data[-1000:]
            
            self.logs_file.write_text(json.dumps(data, indent=2))
    
    async def add_gps_data(self, gps_data: GPSData):
        """Add new GPS data"""
        async with self.lock:
            data = json.loads(self.gps_file.read_text())
            
            data.append(vars(gps_data))
            
            # Keep only last 1000 entries
            if len(data) > 1000:
                data = data[-1000:]
            
            self.gps_file.write_text(json.dumps(data, indent=2))
    
    async def get_recent_logs(self, limit: int = 100) -> List[Dict]:
        """Get recent logs"""
        async with self.lock:
            data = json.loads(self.logs_file.read_text())
            return data[-limit:]
    
    async def get_recent_gps_data(self, device: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """Get recent GPS data, optionally filtered by device"""
        async with self.lock:
            data = json.loads(self.gps_file.read_text())
            if device:
                data = [entry for entry in data if entry["device"] == device]
            return data[-limit:]

# Global data manager instance
data_manager = DataManager() 