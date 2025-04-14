from typing import List, Dict
import asyncio
import json
from datetime import datetime
import os
from dataclasses import dataclass
from enum import Enum

class LogLevel(Enum):
    INFO = "INFO"
    ERROR = "ERROR"
    ACTION = "ACTION"
    WARN = "WARN"
    SECURITY = "SECURITY"

@dataclass
class LogEntry:
    device: str
    level: LogLevel
    message: str
    timestamp: int
    metadata: Dict = None

class LogManager:
    def __init__(self, batch_size: int = 10, flush_interval: float = 5.0):
        self.logs: List[LogEntry] = []
        self.log_queue = asyncio.Queue()
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.is_logging = True
        self.log_file = "app/logs.json"
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
    
    async def add_log(self, device: str, level: LogLevel, message: str, metadata: Dict = None):
        """Add a log entry to the queue"""
        log_entry = LogEntry(
            device=device,
            level=level,
            message=message,
            timestamp=int(datetime.now().timestamp()),
            metadata=metadata
        )
        await self.log_queue.put(log_entry)
    
    async def process_logs(self):
        """Process logs in batches"""
        while self.is_logging:
            try:
                batch = []
                while len(batch) < self.batch_size:
                    try:
                        log = await asyncio.wait_for(self.log_queue.get(), timeout=self.flush_interval)
                        batch.append(log)
                    except asyncio.TimeoutError:
                        break
                
                if batch:
                    await self._save_batch(batch)
                    self.logs.extend(batch)
                    # Keep only last 1000 logs in memory
                    if len(self.logs) > 1000:
                        self.logs = self.logs[-1000:]
            except Exception as e:
                print(f"Error processing logs: {e}")
                await asyncio.sleep(1)
    
    async def _save_batch(self, batch: List[LogEntry]):
        """Save a batch of logs to file"""
        try:
            with open(self.log_file, "a") as f:
                for log in batch:
                    json.dump({
                        "device": log.device,
                        "level": log.level.value,
                        "message": log.message,
                        "timestamp": log.timestamp,
                        "metadata": log.metadata
                    }, f)
                    f.write("\n")
        except Exception as e:
            print(f"Error saving logs: {e}")
    
    def get_recent_logs(self, limit: int = 50) -> List[LogEntry]:
        """Get recent logs"""
        return self.logs[-limit:]
    
    async def stop(self):
        """Stop log processing"""
        self.is_logging = False
        # Process remaining logs
        await self.process_logs()

# Global log manager instance
log_manager = LogManager() 