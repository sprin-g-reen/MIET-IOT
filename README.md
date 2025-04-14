# Smart Helmet System

A FastAPI-based backend for a smart automotive helmet and bike safety system.

## Project Structure

```
smart-helmet/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── filters.py
│   ├── static/
│   └── templates/
│       └── dashboard.html
├── requirements.txt
└── README.md
```

## Features

- Real-time helmet and bike module monitoring
- Automatic bike control based on helmet status
- Comprehensive logging system
- Modern dashboard with Tailwind CSS
- Automatic log persistence
- Device state management

## API Endpoints

### Bike Module
- `GET /bikemodule`
  - Returns plain string status codes:
    - "302" → Start bike
    - "304" → Stop bike
    - "404" → Halt (override via keypad)

### Logging
- `POST /log`
  - Accepts JSON payload:
    ```json
    {
      "device": "bike_module_01" | "helmet_module_01",
      "level": "INFO" | "ERROR" | "ACTION" | "WARN",
      "message": "...",
      "timestamp": 12345678
    }
    ```

### Dashboard
- `GET /dashboard`
  - HTML dashboard showing real-time system status and logs

## Setup

1. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python -m app.main
```

The server will start at `http://localhost:8000`

## Dashboard Features

- Real-time device status monitoring
- Log filtering by level (INFO, ERROR, WARN, ACTION)
- Auto-refresh every 30 seconds
- Responsive design
- Modern UI with Tailwind CSS

## Development

- The application uses FastAPI for the backend
- Frontend is built with Jinja2 templates and Tailwind CSS
- Logs are stored in memory and persisted to `app/logs.json`
- Custom datetime filter for log timestamps

## Security Notes

- Keep sensitive data in environment variables
- Use HTTPS in production
- Regularly monitor logs for suspicious activity
- Implement proper authentication for production use 