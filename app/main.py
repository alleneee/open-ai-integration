import time
import logging
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

# Updated import paths
from app.core.config import settings
from app.api.v1.router import api_router # Import the main v1 router
# Remove direct router imports if they existed
# from app.routers import upload, query
# Import dependencies for startup check if needed (though handled internally now)
from app.services.vector_store import get_milvus_connection, _get_embedding_instance

# Configure logging
logging.basicConfig(level=settings.log_level.upper(), format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.project_name,
    version=settings.project_version,
    openapi_url=f"{settings.api_v1_prefix}/openapi.json",
    docs_url=f"{settings.api_v1_prefix}/docs",
    redoc_url=f"{settings.api_v1_prefix}/redoc"
)

# --- Middleware ---
# CORS
if settings.cors_origins:
    # Convert comma-separated string in env var to list if needed
    origins = []
    if isinstance(settings.cors_origins, str):
        origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
    elif isinstance(settings.cors_origins, list):
        origins = [str(origin) for origin in settings.cors_origins]

    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        logger.info(f"CORS middleware enabled for origins: {origins}")
    else:
        logger.warning("CORS_ORIGINS is set but resulted in an empty list. CORS disabled.")

# Add X-Process-Time header
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = f"{process_time:.4f}"
    logger.debug(f"Request {request.method} {request.url.path} processed in {process_time:.4f} secs")
    return response

# --- Exception Handlers ---
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Log the validation errors for debugging
    logger.error(f"Validation error for request {request.url.path}: {exc.errors()}", extra={"request_path": request.url.path})
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()},
    )

@app.exception_handler(ValidationError) # Catch Pydantic errors specifically if needed elsewhere
async def pydantic_validation_exception_handler(request: Request, exc: ValidationError):
    logger.error(f"Pydantic validation error: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()},
    )

@app.exception_handler(ConnectionError)
async def connection_error_handler(request: Request, exc: ConnectionError):
    logger.error(f"Connection error encountered: {exc}", extra={"request_path": request.url.path})
    # Typically related to Milvus or external services
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": f"Service connection failed: {exc}"}, # Avoid leaking too much detail
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled exception for request {request.url.path}: {exc}") # Log full traceback
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        # Be cautious about returning raw exception messages to clients
        content={"detail": f"An internal server error occurred."}, # Generic message
        # content={"detail": f"An internal server error occurred: {type(exc).__name__}"}, # Slightly more specific
    )

# --- Application Lifecycle ---
@app.on_event("startup")
async def startup_event():
    logger.info("Application startup beginning...")
    # Ensure Milvus connection is attempted at startup
    try:
        get_milvus_connection() # This function now handles connection logic
        logger.info("Milvus connection check successful during startup.")
    except ConnectionError as e:
        logger.critical(f"CRITICAL: Failed to connect to Milvus during startup: {e}. The application might not function correctly.")
        # Decide if you want to exit or continue with degraded functionality
        # raise SystemExit(f"Failed to connect to Milvus: {e}")
    except Exception as e:
         logger.critical(f"CRITICAL: An unexpected error occurred during Milvus connection check at startup: {e}")

    # Initialize embedding model instance (optional, helps catch errors early)
    try:
         _get_embedding_instance()
         logger.info("Embedding model instance initialized successfully during startup.")
    except Exception as e:
         logger.critical(f"CRITICAL: Failed to initialize embedding model during startup: {e}")

    logger.info("Application startup complete.")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutdown beginning...")
    # Clean up resources
    try:
        from pymilvus import connections
        if connections.has_connection("default"):
             connections.disconnect("default")
             logger.info("Milvus connection 'default' closed.")
    except Exception as e:
        logger.error(f"Error disconnecting from Milvus during shutdown: {e}")
    logger.info("Application shutdown complete.")

# --- Routers ---
# Include the main API router
app.include_router(api_router, prefix=settings.api_v1_prefix)

# --- Root Endpoint ---
@app.get("/", tags=["Root"], include_in_schema=False) # Hide root from docs
async def read_root():
    """根路径，提供一个简单的欢迎消息和版本信息。"""
    return {
        "message": f"Welcome to the {settings.project_name}!",
        "version": settings.project_version,
        "docs_url": app.docs_url
        }

# Add health check endpoint
@app.get("/health", tags=["Health Check"], status_code=status.HTTP_200_OK)
async def health_check():
    """执行基本健康检查，检查 Milvus 连接。"""
    # Check Milvus connection status
    milvus_status = "unavailable"
    try:
        from pymilvus import connections, utility
        if not connections.has_connection("default"): get_milvus_connection() # Try connect if not already
        utility.list_collections(using="default") # Lightweight check
        milvus_status = "ok"
    except Exception as e:
        logger.warning(f"Health check: Milvus connection failed - {e}")
        milvus_status = "error"

    # Future: Add checks for LLM availability
    if milvus_status == "ok":
        return {"status": "ok", "milvus_connection": milvus_status}
    else:
         # Return 503 if a critical dependency is down
         raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail={"status": "error", "milvus_connection": milvus_status})
