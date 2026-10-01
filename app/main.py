from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api import health, auth, centres, tests

app = FastAPI(
    title=settings.APP_NAME,
    description="Backend service for diagnostic test bookings and simulated payments.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(centres.router)
app.include_router(tests.router)


@app.get("/")
def root():
    return {
        "message": "Welcome to Eve Healthcare Diagnostic Booking API",
        "docs": "/docs",
        "health": "/health",
    }
