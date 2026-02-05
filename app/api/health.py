"""
Health check endpoints for monitoring.
Implements Kubernetes liveness, readiness, and startup probes.
"""

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from datetime import datetime, timezone
from typing import Dict, Any
from app.config import settings
from app.services.database_service import db_service
from app.utils.logger import logger

# TODO: Uncomment these when we create the services
# from app.services.calendar_service import calendar_service
# from app.services.twilio_service import twilio_service

router = APIRouter(prefix="/health", tags=["health"])

class HealthResponse(BaseModel):
    """Health check response schema."""
    status: str
    timestamp: datetime
    version: str
    environment: str
    services: Dict[str, Any]

@router.get("", response_model=HealthResponse)
async def health_check():
    """
    Liveness probe.
    Returns 200 if the API server process is running.
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc),
        version="1.0.0",
        environment=settings.ENVIRONMENT,
        services={
            "api": "running",
            # We don't check DB here to prevent cascading failures
        }
    )

@router.get("/ready")
async def readiness_check():
    """
    Readiness probe.
    Checks if critical dependencies (Database) are operational.
    """
    health_status = {
        "database": "unknown",
        # "calendar": "unknown", # TODO: Enable later
        # "twilio": "unknown"    # TODO: Enable later
    }
    
    is_ready = True
    
    # 1. Check Database (CRITICAL)
    try:
        db_healthy = await db_service.health_check()
        health_status["database"] = "connected" if db_healthy else "disconnected"
        
        if not db_healthy:
            is_ready = False
            logger.warning("Readiness check failed: Database not connected")
    except Exception as e:
        health_status["database"] = f"error: {str(e)}"
        is_ready = False
    
    # 2. Check Calendar (TODO)
    # try:
    #     if calendar_service.credentials:
    #         health_status["calendar"] = "configured"
    # except Exception as e:
    #     health_status["calendar"] = f"error: {str(e)}"

    # Build response
    response_data = {
        "status": "ready" if is_ready else "not_ready",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": health_status
    }
    
    if is_ready:
        return response_data
    else:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=response_data
        )

@router.get("/startup")
async def startup_check():
    """
    Startup probe.
    Checks if application configuration is loaded.
    """
    try:
        # Simple check: Do we have the critical config variables?
        config_loaded = all([
            settings.SUPABASE_URL,
            settings.GROQ_API_KEY,
            settings.CARTESIA_API_KEY,
            settings.TWILIO_ACCOUNT_SID
        ])
        
        db_ready = await db_service.health_check()
        
        checks = {
            "database": db_ready,
            "config_loaded": config_loaded
        }
        
        all_ready = all(checks.values())
        
        if all_ready:
            return {"status": "started", "checks": checks}
        else:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"status": "starting", "checks": checks}
            )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "startup_failed", "error": str(e)}
        )