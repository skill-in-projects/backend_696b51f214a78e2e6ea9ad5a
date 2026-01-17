import os
import sys
import asyncio
import traceback
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import logging configuration
import logging_config

# Add current directory to path for imports (where main.py is located)
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Note: Models and Controllers are subdirectories of current_dir (root level),
# so they can be imported directly when current_dir is in sys.path

# Get logger
logger = logging.getLogger(__name__)

# Lifespan context manager to handle startup/shutdown gracefully
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application lifespan events - startup and shutdown"""
    # Startup
    logger.warning("Starting Backend API...")
    try:
        yield
    except asyncio.CancelledError:
        # Gracefully handle cancellation during shutdown
        logger.warning("Application shutdown requested")
        raise
    finally:
        # Shutdown
        logger.warning("Shutting down Backend API...")

app = FastAPI(title="Backend API", version="1.0.0", lifespan=lifespan)

# Setup global exception handlers FIRST (before other middleware)
from ExceptionHandler import setup_exception_handlers
setup_exception_handlers(app)

# CORS configuration - allow all origins for GitHub Pages deployments
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (GitHub Pages uses *.github.io)
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, PUT, DELETE, OPTIONS)
    allow_headers=["*"],  # Allow all headers (for CORS preflight)
)

# Import and register router - let it crash if imports fail (this is a build-time error, not runtime)
from Controllers.TestController import router as test_router
app.include_router(test_router)

@app.get("/")
async def root():
    return {
        "message": "Backend API is running",
        "status": "ok",
        "swagger": "/docs",
        "api": "/api/test"
    }

@app.get("/swagger")
async def swagger_redirect():
    """Redirect /swagger to /docs (FastAPI Swagger UI)"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/docs")

@app.get("/health")
async def health():
    """Health check endpoint that doesn't require database"""
    return {
        "status": "healthy",
        "service": "Backend API"
    }

if __name__ == "__main__":
    import uvicorn
    import asyncio
    import traceback
    import httpx
    try:
        port = int(os.getenv("PORT", 8000))
        logger.warning(f"Starting server on 0.0.0.0:{port}")
        # Use lifespan='on' to explicitly enable lifespan handling
        # Configure uvicorn to use WARNING log level
        uvicorn.run(app, host="0.0.0.0", port=port, lifespan="on", log_level="warning")
    except Exception as startup_ex:
        logger.error(f"[STARTUP ERROR] Application failed to start: {startup_ex}", exc_info=True)
        
        # Send startup error to endpoint (fire and forget)
        runtime_error_endpoint_url = os.getenv("RUNTIME_ERROR_ENDPOINT_URL")
        board_id = os.getenv("BOARD_ID")
        
        if runtime_error_endpoint_url:
            try:
                # Extract exception details for startup error
                exc_type = type(startup_ex).__name__
                exc_message = str(startup_ex) if startup_ex else 'Unknown error'
                exc_traceback = ''.join(traceback.format_exception(type(startup_ex), startup_ex, startup_ex.__traceback__))
                
                # Get file and line from traceback
                tb_lines = traceback.extract_tb(startup_ex.__traceback__)
                file_name = tb_lines[-1].filename if tb_lines else None
                line_number = tb_lines[-1].lineno if tb_lines else None
                
                # Build payload for startup error
                payload = {
                    'boardId': board_id,
                    'timestamp': None,  # Will be set by backend
                    'file': file_name,
                    'line': line_number,
                    'stackTrace': exc_traceback,
                    'message': exc_message,
                    'exceptionType': exc_type,
                    'requestPath': 'STARTUP',
                    'requestMethod': 'STARTUP',
                    'userAgent': 'STARTUP_ERROR'
                }
                
                # Send in background (fire and forget) - use threading for sync context
                import threading
                def send_startup_error():
                    try:
                        with httpx.Client(timeout=5.0) as client:
                            client.post(runtime_error_endpoint_url, json=payload)
                    except:
                        pass
                threading.Thread(target=send_startup_error, daemon=True).start()
            except Exception as send_ex:
                # Ignore errors in sending startup error
                pass
        
        raise  # Re-raise to exit with error code
