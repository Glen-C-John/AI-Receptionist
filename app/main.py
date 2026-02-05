"""
Main FastAPI application entry point.
"""
from contextlib import asynccontextmanager
import uuid
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.utils.logger import logger
from app.services.database_service import db_service
from app.api import health


# ==================== MIDDLEWARE ====================

class RequestIDMiddleware(BaseHTTPMiddleware):
    """Adds unique request ID for tracing."""
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        
        return response


# ==================== LIFESPAN MANAGER ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifecycle manager.
    Handles startup and shutdown events.
    """
    # ==================== STARTUP ====================
    logger.info("=" * 60)
    logger.info(f"Starting {settings.APP_NAME}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    logger.info(f"Log level: {settings.LOG_LEVEL}")
    logger.info("=" * 60)
    
    # 1. Verify database connection
    try:
        db_healthy = await db_service.health_check()
        if db_healthy:
            logger.success("✓ Database connection verified")
        else:
            logger.warning("⚠ Database connection failed")
            if settings.ENVIRONMENT == "production":
                raise ConnectionError("Database not available")
    except Exception as e:
        logger.error(f"✗ Database initialization error: {e}")
        if settings.ENVIRONMENT == "production":
            raise
    
    # 2. Verify required environment variables
    required_vars = {
        "SUPABASE_URL": settings.SUPABASE_URL,
        "GROQ_API_KEY": settings.GROQ_API_KEY,
        "CARTESIA_API_KEY": settings.CARTESIA_API_KEY,
        "TWILIO_ACCOUNT_SID": settings.TWILIO_ACCOUNT_SID,
        "TWILIO_AUTH_TOKEN": settings.TWILIO_AUTH_TOKEN,
    }
    
    missing_vars = [name for name, value in required_vars.items() if not value]
    
    if missing_vars:
        logger.error(f"✗ Missing environment variables: {', '.join(missing_vars)}")
        if settings.ENVIRONMENT == "production":
            raise ValueError(f"Missing required env vars: {missing_vars}")
    else:
        logger.success("✓ All required environment variables present")
    
    # 3. Log service status
    logger.info(f"📞 Twilio number: {settings.TWILIO_PHONE_NUMBER}")
    logger.info(f"🏢 Business: {settings.BUSINESS_NAME}")
    logger.info(f"⏰ Business hours: {settings.BUSINESS_HOURS_START} - {settings.BUSINESS_HOURS_END}")
    
    logger.success(f"🚀 {settings.APP_NAME} started successfully")
    logger.info(f"📖 API docs available at: http://{settings.HOST}:{settings.PORT}/docs")
    logger.info("=" * 60)
    
    yield
    
    # ==================== SHUTDOWN ====================
    logger.info("=" * 60)
    logger.info(f"Shutting down {settings.APP_NAME}")
    
    # Close any open connections (if you implement connection pooling)
    # await db_service.close()
    
    logger.success("✓ Shutdown complete")
    logger.info("=" * 60)


# ==================== APP INITIALIZATION ====================

app = FastAPI(
    title=settings.APP_NAME,
    description="AI Voice Receptionist for Car Detailing Business",
    version="1.0.0",
    debug=settings.DEBUG,
    lifespan=lifespan,
    # Customize docs
    docs_url="/docs" if settings.DEBUG else None,  # Hide docs in production
    redoc_url="/redoc" if settings.DEBUG else None,
)


# ==================== MIDDLEWARE ====================

# Request ID tracking
app.add_middleware(RequestIDMiddleware)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== EXCEPTION HANDLERS ====================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors."""
    request_id = getattr(request.state, "request_id", "unknown")
    logger.warning(f"[{request_id}] Validation error on {request.url.path}: {exc.errors()}")
    
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation Error",
            "detail": exc.errors(),
            "request_id": request_id
        }
    )


@app.exception_handler(Exception)
async def internal_error_handler(request: Request, exc: Exception):
    """Catch-all for internal server errors."""
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error(f"[{request_id}] Unhandled Exception on {request.url.path}: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "Something went wrong. Please try again later.",
            "request_id": request_id,
            "detail": str(exc) if settings.DEBUG else None
        }
    )


# ==================== ROUTERS ====================

app.include_router(health.router)

# TODO: Add these as you build them
# app.include_router(webhooks.router)
# app.include_router(websocket.router)


# ==================== ROOT ENDPOINT ====================

@app.get("/")
async def root():
    """Root endpoint for connectivity test."""
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "status": "online",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "docs_url": "/docs" if settings.DEBUG else "disabled in production"
    }


# ==================== MAIN ENTRY POINT ====================

if __name__ == "__main__":
    import uvicorn
    
    if settings.ENVIRONMENT == "production":
        logger.warning(
            "⚠ Running via __main__ in production is not recommended. "
            "Use: gunicorn app.main:app -c gunicorn.conf.py"
        )
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        workers=1,  # CRITICAL: Single worker for WebSocket stability
        access_log=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )