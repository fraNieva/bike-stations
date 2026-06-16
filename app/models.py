from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.database import Base


class StationEvent(Base):
    __tablename__ = "station_events"

    id = Column(Integer, primary_key=True, index=True)
    station_id = Column(String, nullable=False, index=True)
    is_charging = Column(Boolean, nullable=False)
    received_at = Column(DateTime(timezone=True), server_default=func.now())