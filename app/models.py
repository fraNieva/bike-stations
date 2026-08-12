"""
Database models for the bike-stations monitoring system.

Defines the SQLAlchemy ORM models for all four tables:
- User: system administrators who access the dashboard
- Device: registered Arduino boards with their API keys
- StationEvent: raw telemetry received from each device
- Alert: incidents generated when a station stops charging
"""

import enum
from sqlalchemy import (
    Column, Integer, String, Boolean,
    DateTime, Float, Enum, ForeignKey, Text
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class AlertStatus(str, enum.Enum):
    """Possible lifecycle states for an alert."""
    open = "open"
    resolved = "resolved"


class User(Base):
    """
    System user with access to the dashboard and admin endpoints.

    Passwords are never stored in plain text — only bcrypt hashes.
    Multiple users can exist, each independently activatable.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    resolved_alerts = relationship("Alert", back_populates="resolver")


class Device(Base):
    """
    Registered Arduino board installed at a bike station.

    Each device has a unique API key (stored as a bcrypt hash) that it
    must send in every request to the /ingest endpoint. Deactivating a
    device blocks its data without deleting its history.
    """
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    station_id = Column(String, unique=True, nullable=False, index=True)
    api_key_hash = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    registered_at = Column(DateTime(timezone=True), server_default=func.now())
    last_seen_at = Column(DateTime(timezone=True), nullable=True)


class StationEvent(Base):
    """
    Single telemetry reading sent by a device.

    Records the full sensor payload: charging status, voltage, amperage,
    and GPS coordinates. Events older than 7 days are deleted automatically
    by the cleanup scheduler. Alerts are kept permanently.
    """
    __tablename__ = "station_events"

    id = Column(Integer, primary_key=True, index=True)
    station_id = Column(String, nullable=False, index=True)
    is_charging = Column(Boolean, nullable=False)
    voltage = Column(Float, nullable=True)
    amperage = Column(Float, nullable=True)
    gps_lat = Column(Float, nullable=True)
    gps_lng = Column(Float, nullable=True)
    received_at = Column(DateTime(timezone=True), server_default=func.now())


class Alert(Base):
    """
    Incident generated when a station reports two consecutive non-charging events.

    Alerts remain in the database permanently as a historical record.
    A maintenance operator can mark them as resolved, which records
    who resolved it and when.
    """
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    station_id = Column(String, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(Enum(AlertStatus), default=AlertStatus.open, nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    notes = Column(Text, nullable=True)

    resolver = relationship("User", back_populates="resolved_alerts")