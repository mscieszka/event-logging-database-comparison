import random
from pydantic import BaseModel
from datetime import datetime, timedelta

SAMPLE_DATA = {
    "severities": [
        {"name": "INFO", "description": "Informational message"},
        {"name": "WARNING", "description": "Warning condition"},
        {"name": "ERROR", "description": "Error condition"},
        {"name": "CRITICAL", "description": "Critical condition"}
    ],
    "event_types": [
        {"name": "SYSTEM_STATUS", "description": "System status update"},
        {"name": "SECURITY_ALERT", "description": "Security-related event"},
        {"name": "PERFORMANCE", "description": "Performance metric event"},
        {"name": "USER_ACTION", "description": "User-initiated action"},
    ],
    "sources": [
        {
            "name": "web-server-01",
            "ip_address": "192.168.1.100",
            "location": {"name": "PL-01", "country": "Poland", "city": "Katowice"}
        },
        {
            "name": "web-server-02",
            "ip_address": "192.168.1.200",
            "location": {"name": "PL-02", "country": "Poland", "city": "Gdansk"}
        },
        {
            "name": "cache-01",
            "ip_address": "192.168.2.100",
            "location": {"name": "US-01", "country": "USA", "city": "New York"}
        },
        {
            "name": "lb-01",
            "ip_address": "192.168.3.100",
            "location": {"name": "DE-01", "country": "Germany", "city": "Frankfurt"}
        }
    ],
    "messages": {
        "SYSTEM_STATUS": [
            "System startup completed",
            "System shutdown initiated",
            "Service restart required",
            "Memory usage at {}%",
            "CPU utilization peaked at {}%"
        ],
        "SECURITY_ALERT": [
            "Failed login attempt from IP {}",
            "Suspicious activity detected",
            "Firewall rule updated",
            "New security patch applied",
            "User account locked after {} attempts"
        ],
        "PERFORMANCE": [
            "Response time exceeded {}ms",
            "Database query took {}ms",
            "Network latency increased to {}ms",
            "Queue size reached {}"
        ],
        "USER_ACTION": [
            "User {} logged in successfully",
            "Password change attempted",
            "Configuration updated by admin",
            "New user account created"
        ],
    }
}

class Location(BaseModel):
    name: str
    country: str
    city: str

class Source(BaseModel):
    name: str
    ip_address: str
    location: Location

class EventType(BaseModel):
    name: str
    description: str

class Severity(BaseModel):
    name: str
    description: str

class Event(BaseModel):
    timestamp: datetime
    message: str
    severity: Severity
    event_type: EventType
    source: Source

class UpdateEventSeverity(BaseModel):
    timestamp: datetime
    old_severity: str
    new_severity: str
    event_type: str
    source_name: str

class Utilities:
    @staticmethod
    def get_random_event_json() -> dict:
        reference_time = datetime.now()
        time_variation = timedelta(hours=random.uniform(-12, 12))
        timestamp = reference_time + time_variation

        severity = random.choice(SAMPLE_DATA["severities"])
        event_type = random.choice(SAMPLE_DATA["event_types"])
        source = random.choice(SAMPLE_DATA["sources"])

        message_template = random.choice(SAMPLE_DATA["messages"][event_type["name"]])
        message = message_template.format(
            *[random.randint(1, 100) for _ in range(message_template.count("{}"))]
        )

        return {
            "timestamp": timestamp.isoformat(),
            "message": message,
            "severity": severity,
            "event_type": event_type,
            "source": source
        }
