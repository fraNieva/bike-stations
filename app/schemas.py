"""
Pydantic schemas for request validation and response serialization.

Each schema is a contract between the API and its consumers (dashboard,
Arduino devices, admin tools). Keeping schemas separate from ORM models
lets both evolve independently.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from app.models import AlertStatus


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    """Credentials submitted to obtain a JWT access token."""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """JWT token returned after a successful login."""
    access_token: str
    token_type: str = "bearer"


# ---------------------------------------------------------------------------
# Devices
# ---------------------------------------------------------------------------

class DeviceCreate(BaseModel):
    """Payload required to register a new Arduino device."""
    station_id: str
    api_key: str


class DeviceUpdate(BaseModel):
    """Partial update for a device — only provided fields are changed."""
    is_active: Optional[bool] = None


class DeviceResponse(BaseModel):
    """Device data returned by the API (api_key_hash is never exposed)."""
    id: int
    station_id: str
    is_active: bool
    registered_at: datetime
    last_seen_at: Optional[datetime]

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

class UserCreate(BaseModel):
    """Payload required to create a new dashboard user."""
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    """Partial update for a user — only provided fields are changed."""
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    """User data returned by the API (password_hash is never exposed)."""
    id: int
    email: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Ingest
# ---------------------------------------------------------------------------

class IngestPayload(BaseModel):
    """
    Telemetry payload sent by an Arduino device every 10-15 minutes.

    station_id must match a registered and active device in the database.
    voltage and amperage are optional for phase-1 devices that only
    report charging status.
    """
    station_id: str
    is_charging: bool
    voltage: Optional[float] = None
    amperage: Optional[float] = None
    gps_lat: Optional[float] = None
    gps_lng: Optional[float] = None
    timestamp: Optional[datetime] = None


class IngestResponse(BaseModel):
    """Confirmation returned to the device after a successful ingest."""
    id: int
    station_id: str
    is_charging: bool
    received_at: datetime
    alert_created: bool

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Station events
# ---------------------------------------------------------------------------

class StationEventResponse(BaseModel):
    """Single telemetry reading as returned by the dashboard API."""
    id: int
    station_id: str
    is_charging: bool
    voltage: Optional[float]
    amperage: Optional[float]
    gps_lat: Optional[float]
    gps_lng: Optional[float]
    received_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------

class AlertResponse(BaseModel):
    """Alert record as returned by the dashboard API."""
    id: int
    station_id: str
    created_at: datetime
    status: AlertStatus
    resolved_at: Optional[datetime]
    resolved_by: Optional[int]
    notes: Optional[str]

    model_config = {"from_attributes": True}


class AlertResolve(BaseModel):
    """Payload to mark an alert as resolved."""
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------

class StationAlertSummary(BaseModel):
    """Per-station metrics within an alerts report."""
 
    station_id: str
    total: int
    open: int
    resolved: int
    avg_resolution_minutes: Optional[float] = None
 
 
class ReportPeriod(BaseModel):
    """Date range covered by a report."""
 
    from_date: Optional[datetime] = Field(None, alias="from")
    to_date: Optional[datetime] = Field(None, alias="to")
 
    model_config = ConfigDict(populate_by_name=True)
 
 
class AlertsReportResponse(BaseModel):
    """Response schema for GET /reports/alerts."""
 
    total: int
    open: int
    resolved: int
    avg_resolution_minutes: Optional[float] = None
    by_station: Optional[list[StationAlertSummary]] = None
    period: ReportPeriod
 