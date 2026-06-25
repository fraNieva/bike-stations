"""
Bike Stations Monitoring API.

Entry point for the FastAPI application. Registers all routers,
exposes a health check endpoint, and manages the background scheduler
lifecycle via the FastAPI lifespan context manager.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.routers import auth, ingest, alerts, stations, admin, reports
from app.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s  [%(name)s] %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start the background scheduler on startup and stop it on shutdown."""
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="Bike Stations Monitoring API",
    description="Receives telemetry from Arduino devices and exposes data to the dashboard.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(auth.router)
app.include_router(ingest.router)
app.include_router(alerts.router)
app.include_router(stations.router)
app.include_router(admin.router)
app.include_router(reports.router)


@app.get("/health", tags=["system"])
def health_check():
    """
    Returns a simple ok status.

    Used by Railway and load balancers to verify the service is alive.
    No authentication required.
    """
    return {"status": "ok"}