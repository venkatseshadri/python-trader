# orbiter/utils/json_helpers.py

from datetime import datetime
import json

class JSONEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle datetime objects."""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return json.JSONEncoder.default(self, obj)

def json_serial(obj):
    """Fallback for direct calls (deprecated). Use JSONEncoder class."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")
