from datetime import datetime

def format_datetime(timestamp):
    """Convert Unix timestamp to formatted datetime string"""
    try:
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return "Invalid timestamp" 