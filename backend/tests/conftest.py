import pytest

from models.query import TripQuery
from models.results import ProviderCategory, ProviderResult, TripCombo, TripSuggestion


@pytest.fixture
def sample_query():
    return TripQuery(origin_iata="ATL", budget_usd=2000.0, duration_days=4, travelers=2)


@pytest.fixture
def sample_flight():
    return ProviderResult(
        provider="amadeus",
        category=ProviderCategory.FLIGHT,
        destination_iata="LAS",
        destination_name="Las Vegas, United States",
        title="Round-trip flight ATL → LAS",
        price_usd=400.0,
        affiliate_url="https://amadeus.example.com/flight/LAS",
    )


@pytest.fixture
def sample_hotel():
    return ProviderResult(
        provider="booking",
        category=ProviderCategory.HOTEL,
        destination_iata="LAS",
        destination_name="Las Vegas, United States",
        title="Bellagio Hotel — 4 nights",
        price_usd=600.0,
        affiliate_url="https://booking.example.com/hotel/LAS",
    )


@pytest.fixture
def sample_car():
    return ProviderResult(
        provider="enterprise",
        category=ProviderCategory.CAR_RENTAL,
        destination_iata="LAS",
        destination_name="Las Vegas, United States",
        title="Economy Car — 4 days",
        price_usd=180.0,
        affiliate_url="https://enterprise.example.com/car/LAS",
    )


@pytest.fixture
def sample_attraction():
    return ProviderResult(
        provider="viator",
        category=ProviderCategory.ATTRACTION,
        destination_iata="LAS",
        destination_name="Las Vegas, United States",
        title="Las Vegas Strip Night Tour",
        price_usd=98.0,  # $49/person × 2 travelers
        affiliate_url="https://www.viator.com/search/LAS",
    )


@pytest.fixture
def sample_combo(sample_flight, sample_hotel, sample_car, sample_attraction):
    return TripCombo(
        destination_iata="LAS",
        destination_name="Las Vegas, United States",
        flight=sample_flight,
        hotel=sample_hotel,
        car_rental=sample_car,
        attractions=[sample_attraction],
        total_cost=1278.0,
    )


@pytest.fixture
def sample_suggestion():
    return TripSuggestion(
        rank=1,
        destination="Las Vegas, United States",
        destination_iata="LAS",
        total_cost=1278.0,
        breakdown={"flight": 400.0, "hotel": 600.0, "car_rental": 180.0, "attractions": 98.0},
        ai_summary="Las Vegas delivers spectacular value with world-class entertainment.",
        highlights=["Strip Night Tour ($98)", "Bellagio Hotel", "Economy Car included"],
        ranking_reason="Best value-for-money of all candidates.",
        affiliate_links={
            "flight": "https://amadeus.example.com/flight/LAS",
            "hotel": "https://booking.example.com/hotel/LAS",
            "car_rental": "https://enterprise.example.com/car/LAS",
            "attractions": "https://www.viator.com/search/LAS",
        },
    )
