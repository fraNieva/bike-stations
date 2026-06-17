"""
Bike Stations Monitoring API.

Entry point for the FastAPI application. Registers all routers and
exposes a health check endpoint used by Railway to verify the service
is running correctly.
"""

from fastapi import FastAPI
from app.database import engine
from app import models

app = FastAPI(
    title="Bike Stations Monitoring API",
    description="Receives telemetry from Arduino devices and exposes data to the dashboard.",
    version="0.1.0",
)


@app.get("/health", tags=["system"])
def health_check():
    """
    Returns a simple ok status.

    Used by Railway and load balancers to verify the service is alive.
    No authentication required.
    """
    return {"status": "ok"}