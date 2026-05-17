from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from datetime import datetime


class CreateMonitorRequest(BaseModel):
    id: str = Field(..., min_length=1, max_length=128, description="Unique device identifier")
    timeout: int = Field(..., ge=5, le=86400, description="Countdown duration in seconds (5s – 24h)")
    alert_email: EmailStr = Field(..., description="Email to notify when device goes silent")

    model_config = {"json_schema_extra": {"example": {"id": "device-123", "timeout": 60, "alert_email": "admin@critmon.com"}}}


class MonitorResponse(BaseModel):
    id: str
    timeout: int
    alert_email: str
    status: str
    created_at: datetime
    last_ping_at: Optional[datetime]
    deadline: Optional[datetime]
    alert_fired: bool


class MessageResponse(BaseModel):
    message: str
    monitor_id: str
