import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from routers import trips

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)

app = FastAPI(
    title="TravelBuddy API",
    description="AI-powered trip package search: flights + hotel + car + attractions.",
    version="0.1.0",
)

_origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "https://packednbooked.com",
    "https://www.packednbooked.com",
]
if settings.frontend_url and settings.frontend_url not in _origins:
    _origins.append(settings.frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(trips.router, prefix="/api")

logger = logging.getLogger(__name__)

