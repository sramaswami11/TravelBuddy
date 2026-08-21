from pydantic import BaseModel, Field
from typing import Optional
from datetime import date


class TripQuery(BaseModel):
    """Top-level request from the user."""
    origin_iata: str = Field(..., description="Origin airport IATA code", examples=["JFK", "LAX"])
    budget_usd: float = Field(..., gt=0, description="Total trip budget in USD")
    duration_days: int = Field(..., ge=1, le=30, description="Number of days for the trip")
    travelers: int = Field(default=1, ge=1, le=10)
    departure_date: Optional[date] = Field(default=None, description="Specific departure date; None means flexible")


class SearchQuery(BaseModel):
    """Normalized query passed to each factory/agent."""
    origin_iata: str
    destination_iata: Optional[str] = None  # None = inspiration search (find cheapest destinations)
    destination_name: Optional[str] = None
    budget_usd: float
    duration_days: int
    travelers: int
    departure_date: Optional[date] = None
