from typing import Dict, List, Optional
import json
import asyncio
from datetime import datetime
import os
from dataclasses import dataclass
import aiohttp
from fastapi import HTTPException

@dataclass
class GPSData:
    device: str
    latitude: float
    longitude: float
    timestamp: str
    ip_location: Optional[Dict] = None

class GPSManager:
    def __init__(self, file_path: str = "app/gps.json"):
        self.file_path = file_path
        self.gps_data: List[GPSData] = []
        self.lock = asyncio.Lock()
        self._load_data()
    
    def _load_data(self):
        """Load GPS data from JSON file"""
        if os.path.exists(self.file_path):
            with open(self.file_path, 'r') as f:
                data = json.load(f)
                self.gps_data = [GPSData(**entry) for entry in data]
    
    def _save_data(self):
        """Save GPS data to JSON file"""
        with open(self.file_path, 'w') as f:
            json.dump([vars(entry) for entry in self.gps_data], f, indent=2)
    
    async def add_gps_data(self, device: str, latitude: float, longitude: float, ip: Optional[str] = None) -> GPSData:
        """Add new GPS data with optional IP location"""
        async with self.lock:
            ip_location = None
            if ip:
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(f"http://ip-api.com/json/{ip}") as response:
                            if response.status == 200:
                                ip_location = await response.json()
                except Exception as e:
                    print(f"Error fetching IP location: {e}")
            
            gps_entry = GPSData(
                device=device,
                latitude=latitude,
                longitude=longitude,
                timestamp=datetime.now().isoformat(),
                ip_location=ip_location
            )
            
            self.gps_data.append(gps_entry)
            # Keep only last 1000 entries
            if len(self.gps_data) > 1000:
                self.gps_data = self.gps_data[-1000:]
            
            self._save_data()
            return gps_entry
    
    def get_device_locations(self, device: str, limit: int = 10) -> List[GPSData]:
        """Get recent GPS locations for a device"""
        return [entry for entry in self.gps_data if entry.device == device][-limit:]
    
    def get_all_locations(self, limit: int = 100) -> List[GPSData]:
        """Get recent GPS locations for all devices"""
        return self.gps_data[-limit:]

# Global GPS manager instance
gps_manager = GPSManager() 