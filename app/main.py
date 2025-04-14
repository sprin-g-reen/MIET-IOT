from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, HTTPException, Query, Body
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from typing import List, Dict, Set, Optional
import os
from pathlib import Path
import asyncio
import json
import csv
import io
from .device_manager import device_manager, DeviceType, DeviceStatus
from .log_manager import log_manager, LogLevel
from .gps_manager import gps_manager, GPSData
from twilio.rest import Client
from pydantic import BaseModel
from .data_manager import data_manager, DeviceStatus, GPSData

# Create app directory if it doesn't exist
os.makedirs("app/static", exist_ok=True)
os.makedirs("app/templates", exist_ok=True)

app = FastAPI(title="Smart Helmet System")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# Initialize Twilio client
twilio_client = Client(
    os.getenv("TWILIO_ACCOUNT_SID"),
    os.getenv("TWILIO_AUTH_TOKEN")
)

# WebSocket connections
active_connections: Set[WebSocket] = set()

class DrunkenAlert(BaseModel):
    uuid: str
    alcohol_level: int
    timestamp: str

class GPSData(BaseModel):
    device: str
    latitude: float
    longitude: float
    ip: Optional[str] = None

class LogEntry(BaseModel):
    device: str
    level: str
    message: str
    timestamp: Optional[str] = None

async def broadcast_event(event_type: str, data: Dict):
    """Broadcast event to all connected WebSocket clients"""
    for connection in active_connections:
        try:
            await connection.send_json({
                "type": event_type,
                "data": data
            })
        except:
            active_connections.remove(connection)

# Custom datetime filter for Jinja2
def format_datetime(value, format="%Y-%m-%d %H:%M:%S"):
    if isinstance(value, str):
        try:
            # Try to parse ISO format string
            dt = datetime.fromisoformat(value)
            return dt.strftime(format)
        except ValueError:
            return value
    elif isinstance(value, datetime):
        return value.strftime(format)
    return str(value)

templates.env.filters["datetime"] = format_datetime

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}  # device_id -> WebSocket

    async def connect(self, device_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[device_id] = websocket

    def disconnect(self, device_id: str):
        if device_id in self.active_connections:
            del self.active_connections[device_id]

    async def send_to_device(self, device_id: str, message: str):
        if device_id in self.active_connections:
            await self.active_connections[device_id].send_text(message)

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.add(websocket)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_connections.remove(websocket)

@app.on_event("startup")
async def startup_event():
    # Start log processing task
    asyncio.create_task(log_manager.process_logs())

@app.on_event("shutdown")
async def shutdown_event():
    await log_manager.stop()

@app.post("/drunken")
async def drunken_alert(uuid: str, alcohol_level: int, timestamp: str):
    """Handle alcohol detection alert"""
    status = DeviceStatus(
        uuid=uuid,
        status="drunken",
        timestamp=timestamp,
        alcohol_level=alcohol_level
    )
    
    await data_manager.update_device_status(status)
    await data_manager.add_log(uuid, "SECURITY", f"Alcohol detected: {alcohol_level}")
    
    # Send SMS alert
    try:
        twilio_client.messages.create(
            body=f"🚨 ALERT: Alcohol detected in helmet {uuid} (Level: {alcohol_level})",
            from_=os.getenv("TWILIO_PHONE_NUMBER"),
            to=os.getenv("ALERT_PHONE_NUMBER")
        )
    except Exception as e:
        await data_manager.add_log(uuid, "ERROR", f"Failed to send SMS: {str(e)}")
    
    # Broadcast status update
    await broadcast_event("status_update", {
        "device": uuid,
        "status": "drunken",
        "timestamp": timestamp
    })
    
    # Send 304 to bike to block it
    await manager.send_to_device("bike-001", "304")
    
    return {"status": "alert processed"}

@app.get("/not_drunken")
async def not_drunken(uuid: str = Query(...)):
    """Handle safe helmet status update"""
    status = DeviceStatus(
        uuid=uuid,
        status="not_drunken",
        timestamp=datetime.now().isoformat()
    )
    
    await data_manager.update_device_status(status)
    await data_manager.add_log(uuid, "ACTION", "Helmet status: Safe")
    
    # Send 302 to bike to allow it
    await manager.send_to_device("bike-001", "302")
    
    # Broadcast status update
    await broadcast_event("status_update", {
        "device": uuid,
        "status": "not_drunken",
        "timestamp": status.timestamp
    })
    
    return {"status": "updated"}

@app.get("/bikemodule_webhook")
async def bike_webhook(uuid: str = Query(...)):
    """Webhook endpoint for bike module to check helmet status"""
    status = await data_manager.get_device_status(uuid)
    
    if not status:
        return JSONResponse(
            status_code=404,
            content={"status": "helmet not paired"}
        )
    
    if status.status == "drunken":
        return JSONResponse(
            status_code=304,
            content={"status": "block bike"}
        )
    
    return JSONResponse(
        status_code=302,
        content={"status": "start bike"}
    )

@app.post("/GPS")
async def update_gps(device: str, latitude: float, longitude: float, timestamp: str):
    """Update GPS location"""
    gps_data = GPSData(
        device=device,
        latitude=latitude,
        longitude=longitude,
        timestamp=timestamp
    )
    
    await data_manager.add_gps_data(gps_data)
    
    # Broadcast GPS update
    await broadcast_event("gps_update", {
        "device": device,
        "latitude": latitude,
        "longitude": longitude,
        "timestamp": timestamp
    })
    
    return {"status": "updated"}

@app.post("/log")
async def add_log(log: LogEntry = Body(...)):
    """Add new log entry"""
    await data_manager.add_log(log.device, log.level, log.message)
    return {"status": "logged"}

@app.post("/PostLogs")
async def post_logs(log: LogEntry = Body(...)):
    """Add new log entry"""
    # If no timestamp provided, use current time
    if not log.timestamp:
        log.timestamp = datetime.now().isoformat()
    
    await data_manager.add_log(log.device, log.level, log.message)
    return {"status": "logged"}

@app.get("/dashboard")
async def dashboard(request: Request):
    """Render dashboard with current status and GPS data"""
    # Get recent logs
    logs = await data_manager.get_recent_logs()
    
    # Get recent GPS data for both devices
    helmet_gps = await data_manager.get_recent_gps_data("helmet-001", limit=1)
    bike_gps = await data_manager.get_recent_gps_data("bike-001", limit=1)
    
    # Get current status for both devices
    helmet_status = await data_manager.get_device_status("helmet-001")
    bike_status = await data_manager.get_device_status("bike-001")
    
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "logs": logs,
            "helmet_gps": helmet_gps[0] if helmet_gps else None,
            "bike_gps": bike_gps[0] if bike_gps else None,
            "helmet_status": helmet_status.status if helmet_status else "unknown",
            "bike_status": bike_status.status if bike_status else "unknown",
            "last_update": datetime.now().isoformat()
        }
    )

@app.get("/export/logs")
async def export_logs(format: str = "json"):
    """Export logs in JSON or CSV format"""
    logs = log_manager.get_recent_logs(limit=1000)
    
    if format.lower() == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Timestamp", "Device", "Level", "Message"])
        for log in logs:
            writer.writerow([
                log.timestamp,
                log.device,
                log.level,
                log.message
            ])
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=logs.csv"}
        )
    else:
        return JSONResponse(
            content=[vars(log) for log in logs],
            headers={"Content-Disposition": "attachment; filename=logs.json"}
        )

@app.websocket("/ws/bike-001")
async def bike_websocket(websocket: WebSocket):
    """WebSocket endpoint for bike module"""
    await manager.connect("bike-001", websocket)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect("bike-001")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 