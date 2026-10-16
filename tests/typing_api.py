"""Type-level public API regressions, checked by `uv run mypy`."""

from datetime import datetime, timedelta

from typing_extensions import assert_type

from pytmb import BusClient, MetroClient, PlannerClient, TMBClient, TransitClient
from pytmb.models import (
    BusArrivals,
    BusEtaResponse,
    BusRouteInfo,
    BusRoutesConsolidatedResponse,
    BusRoutesResponse,
    Leg,
    LineInfo,
    LinesResponse,
    LineString,
    MetroArrivals,
    MetroEtaResponse,
    MultiLineString,
    PlannerResponse,
    PlannerSummary,
)
from pytmb.summaries import summarize_bus, summarize_bus_routes, summarize_lines, summarize_metro, summarize_plan


def check_bus_types(client: BusClient) -> None:
    assert_type(client.fetch_eta("1234"), BusEtaResponse)
    view = summarize_bus(client.fetch_eta("1234"))
    assert_type(view, BusArrivals)
    assert_type(view.observed_at, datetime)
    assert_type(view.arrivals[0].eta, timedelta)
    assert_type(view.arrivals[0].eta_minutes, int)
    assert_type(view.arrivals[0].ramp_status, str | None)
    assert_type(view.arrivals[0].line_code, int | str)
    assert_type(view.arrivals[0].bus_id, int | None)


def check_metro_types(client: MetroClient) -> None:
    assert_type(client.fetch_eta([123]), MetroEtaResponse)
    view = summarize_metro(client.fetch_eta([123]))
    assert_type(view, MetroArrivals)
    assert_type(view.arrivals[0].track, int)
    assert_type(view.arrivals[0].arrival_at, datetime)


def check_planner_types(client: PlannerClient) -> None:
    origin = (41.4, 2.18)
    destination = (41.41, 2.16)
    assert_type(client.fetch_plan(origin, destination), PlannerResponse)
    view = summarize_plan(client.fetch_plan(origin, destination))
    assert_type(view, PlannerSummary)
    assert_type(view.itineraries[0].walk_distance, float | None)
    assert_type(view.itineraries[0].transit_time, timedelta | None)
    assert_type(view.itineraries[0].legs, list[Leg])
    assert_type(view.itineraries[0].duration_seconds, float)


def check_transit_types(client: TransitClient) -> None:
    assert_type(client.fetch_lines("bus"), LinesResponse)
    assert_type(client.fetch_bus_routes(10), BusRoutesResponse)
    assert_type(client.fetch_consolidated_bus_routes(10), BusRoutesConsolidatedResponse)
    assert_type(summarize_lines(client.fetch_lines("bus")), list[LineInfo])
    assert_type(summarize_bus_routes(client.fetch_bus_routes(10)), list[BusRouteInfo])
    collection = client.fetch_lines("bus")
    assert_type(collection.total_features, int)
    assert_type(collection.number_returned, int | None)
    assert_type(collection.timestamp, str | None)
    geometry = collection.features[0].geometry
    if geometry.type_ == "LineString":
        assert_type(geometry, LineString)
        assert_type(geometry.coordinates, list[tuple[float, float]])
    else:
        assert_type(geometry, MultiLineString)
        assert_type(geometry.coordinates, list[list[tuple[float, float]]])


def check_facade_types(client: TMBClient) -> None:
    assert_type(client.bus, BusClient)
    assert_type(client.metro, MetroClient)
    assert_type(client.planner, PlannerClient)
    assert_type(client.transit, TransitClient)
    assert_type(client.closed, bool)
    with client as entered:
        assert_type(entered, TMBClient)
    with client.bus as bus:
        assert_type(bus, BusClient)
