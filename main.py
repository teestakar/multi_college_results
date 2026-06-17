from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from config import settings
from database.database import init_db, engine
from routers.health import router as health_router
from routers.auth import router as auth_router
from routers.results import router as results_router
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi.responses import JSONResponse

# ==================== STARTUP/SHUTDOWN ====================
async def startup():
    """
    Called when app starts.
    Creates all tables in PostgreSQL.
    """
    print("🚀 Starting application...")
    await init_db()
    print("✅ Database tables created/verified")

async def shutdown():
    """
    Called when app shuts down.
    Cleanup if needed.
    """
    print("🛑 Shutting down application...")

# Lifespan context manager (FastAPI 0.93+)
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup and shutdown events"""
    await startup()
    yield
    await shutdown()

# ==================== FASTAPI APP ====================
app = FastAPI(
    title="Multi-College Result Platform",
    description="Backend API for multi-tenancy result management system",
    version="1.0.0",
    lifespan=lifespan
)

# Add rate limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

# Handle rate limit errors
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request, exc):
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests. Please try again later."}
    )


# ==================== CORS ====================
# Allow frontend to make requests from different domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, change to ["https://yourdomain.com"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== ROUTERS ====================
app.include_router(health_router)
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(results_router, prefix="/api/results", tags=["results"])  # ← ADD THIS

# ==================== ROOT ENDPOINT ====================
@app.get("/")
async def root():
    """Welcome message"""
    return {
        "message": "Welcome to Multi-College Result Platform",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "docs": "/docs",
        "health": "/health"
    }

# ==================== RUN ====================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True  # Auto-reload on code change (dev only)
    )