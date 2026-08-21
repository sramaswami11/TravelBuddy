import pytest
from pydantic import ValidationError

from models.query import TripQuery
from models.results import ProviderCategory, ProviderResult, TripCombo


# --- TripQuery validation ---

def test_trip_query_defaults():
    q = TripQuery(origin_iata="ATL", budget_usd=500, duration_days=3)
    assert q.travelers == 1
    assert q.departure_date is None


@pytest.mark.parametrize("budget", [0, -1, -100])
def test_trip_query_non_positive_budget_is_invalid(budget):
    with pytest.raises(ValidationError):
        TripQuery(origin_iata="ATL", budget_usd=budget, duration_days=3)


@pytest.mark.parametrize("days", [0, 31, 100])
def test_trip_query_out_of_range_duration_is_invalid(days):
    with pytest.raises(ValidationError):
        TripQuery(origin_iata="ATL", budget_usd=1000, duration_days=days)


@pytest.mark.parametrize("travelers", [0, 11, 50])
def test_trip_query_out_of_range_travelers_is_invalid(travelers):
    with pytest.raises(ValidationError):
        TripQuery(origin_iata="ATL", budget_usd=1000, duration_days=3, travelers=travelers)


def test_trip_query_boundary_values_are_valid():
    TripQuery(origin_iata="ATL", budget_usd=0.01, duration_days=1, travelers=1)
    TripQuery(origin_iata="ATL", budget_usd=99999, duration_days=30, travelers=10)


# --- TripCombo.breakdown ---

def test_combo_breakdown_all_components(sample_combo):
    bd = sample_combo.breakdown
    assert bd["flight"] == 400.0
    assert bd["hotel"] == 600.0
    assert bd["car_rental"] == 180.0
    assert bd["attractions"] == 98.0


def test_combo_breakdown_no_car(sample_flight, sample_hotel, sample_attraction):
    combo = TripCombo(
        destination_iata="LAS",
        destination_name="Las Vegas, United States",
        flight=sample_flight,
        hotel=sample_hotel,
        car_rental=None,
        attractions=[sample_attraction],
        total_cost=1098.0,
    )
    assert combo.breakdown["car_rental"] == 0.0


def test_combo_breakdown_no_attractions(sample_flight, sample_hotel):
    combo = TripCombo(
        destination_iata="LAS",
        destination_name="Las Vegas, United States",
        flight=sample_flight,
        hotel=sample_hotel,
        total_cost=1000.0,
    )
    assert combo.breakdown["attractions"] == 0.0


def test_combo_breakdown_multiple_attractions(sample_flight, sample_hotel, sample_attraction):
    attraction2 = sample_attraction.model_copy(update={"title": "Hoover Dam Tour", "price_usd": 158.0})
    combo = TripCombo(
        destination_iata="LAS",
        destination_name="Las Vegas, United States",
        flight=sample_flight,
        hotel=sample_hotel,
        attractions=[sample_attraction, attraction2],
        total_cost=1156.0,
    )
    assert combo.breakdown["attractions"] == pytest.approx(256.0)
