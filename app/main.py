from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db, engine
from app import models

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Bike Stations POC")


class StationStatusPayload(BaseModel):
    station_id: str
    is_charging: bool


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/status", status_code=201)
def receive_status(payload: StationStatusPayload, db: Session = Depends(get_db)):
    event = models.StationEvent(
        station_id=payload.station_id,
        is_charging=payload.is_charging,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return {
        "id": event.id,
        "station_id": event.station_id,
        "is_charging": event.is_charging,
        "received_at": event.received_at,
    }


@app.get("/status/{station_id}")
def get_station_status(station_id: str, db: Session = Depends(get_db)):
    events = (
        db.query(models.StationEvent)
        .filter(models.StationEvent.station_id == station_id)
        .order_by(models.StationEvent.received_at.desc())
        .limit(10)
        .all()
    )
    if not events:
        raise HTTPException(status_code=404, detail="Station not found")
    return [
        {
            "id": e.id,
            "station_id": e.station_id,
            "is_charging": e.is_charging,
            "received_at": e.received_at,
        }
        for e in events
    ]