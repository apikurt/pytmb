"""Convenience transformations that do not perform HTTP requests."""

from datetime import datetime, timedelta, timezone

from pytmb.enums import TransitMode
from pytmb.exceptions import ResponseValidationError
from pytmb.models.bus import BusEtaResponse
from pytmb.models.metro import MetroEtaResponse
from pytmb.models.planner import Itinerary, PlannerResponse
from pytmb.models.summaries import (
    BusArrival,
    BusArrivals,
    ItinerarySummary,
    MetroArrival,
    MetroArrivals,
    PlannerSummary,
)
from pytmb.models.transit.lines import LineInfo, LinesResponse
from pytmb.models.transit.routes import BusRouteInfo, BusRoutesConsolidatedResponse, BusRoutesResponse


__all__ = [
    "filter_bus",
    "filter_metro",
    "summarize_bus",
    "summarize_metro",
    "summarize_plan",
    "summarize_lines",
    "summarize_bus_routes",
]

_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def _from_millis(milliseconds: int) -> datetime:
    return _EPOCH + timedelta(milliseconds=milliseconds)


def _reference_time(timestamp: int, at: datetime | None) -> datetime:
    if at is None:
        return _from_millis(timestamp)
    if not isinstance(at, datetime) or at.utcoffset() is None:
        raise ValueError("at must be a timezone-aware datetime")
    return at.astimezone(timezone.utc)


def filter_bus(response: BusEtaResponse, line: str) -> BusEtaResponse:
    """Return an independent typed subset, keeping stops even when they have no matching routes."""
    target = line.strip().lower()
    result = response.model_copy(deep=True)
    for stop in result.stops:
        stop.line_routes = [route for route in stop.line_routes if route.line_name.lower() == target]
    return result


def filter_metro(response: MetroEtaResponse, line: str) -> MetroEtaResponse:
    """Return an independent typed subset containing matching top-level lines."""
    target = line.strip().lower()
    result = response.model_copy(deep=True)
    result.lines = [metro_line for metro_line in result.lines if metro_line.line_name.lower() == target]
    return result


def summarize_bus(
    response: BusEtaResponse, *, line: str | None = None, at: datetime | None = None, include_past: bool = False
) -> BusArrivals:
    """Flatten predictions relative to the response timestamp or an explicit aware `at`.

    Past arrivals are omitted by default. Conversion reads no clock and never
    modifies the response. Observation and reference times are retained in UTC.
    """
    reference = _reference_time(response.timestamp, at)
    target = line.strip().lower() if line is not None else None
    arrivals: list[BusArrival] = []
    for stop in response.stops:
        for route in stop.line_routes:
            if target is not None and route.line_name.lower() != target:
                continue
            for bus in route.upcoming_buses:
                arrival_at = _from_millis(bus.arrival_time)
                if not include_past and arrival_at < reference:
                    continue
                arrivals.append(
                    BusArrival(
                        line_code=route.line_code,
                        line_name=route.line_name,
                        destination=route.destination,
                        route_code=route.route_code,
                        direction_id=route.direction_id,
                        operator_id=route.operator_id,
                        transit_namespace=route.transit_namespace,
                        stop_code=stop.stop_code,
                        stop_name=stop.stop_name,
                        bus_id=bus.bus_id,
                        arrival_at=arrival_at,
                        eta=arrival_at - reference,
                        ramp_status=bus.info.accessibility.ramp_status
                        if bus.info is not None and bus.info.accessibility is not None
                        else None,
                    )
                )
    return BusArrivals(observed_at=_from_millis(response.timestamp), reference_time=reference, arrivals=arrivals)


def summarize_metro(
    response: MetroEtaResponse, *, line: str | None = None, at: datetime | None = None, include_past: bool = False
) -> MetroArrivals:
    """Flatten metro predictions without losing direction, track, service, or timestamps.

    The default reference time is the response timestamp; `at` must be timezone-aware.
    Conversion reads no clock. Past predictions are omitted unless requested.
    """
    reference = _reference_time(response.timestamp, at)
    target = line.strip().lower() if line is not None else None
    arrivals: list[MetroArrival] = []
    for metro_line in response.lines:
        if target is not None and metro_line.line_name.lower() != target:
            continue
        for station in metro_line.stations:
            for route in station.line_routes:
                for train in route.upcoming_trains:
                    arrival_at = _from_millis(train.arrival_time)
                    if not include_past and arrival_at < reference:
                        continue
                    arrivals.append(
                        MetroArrival(
                            line_code=metro_line.line_code,
                            line_name=metro_line.line_name,
                            line_color=metro_line.line_color,
                            destination=route.destination,
                            route_code=route.route_code,
                            direction_id=station.direction_id,
                            station_code=station.station_code,
                            track=station.track,
                            service_code=train.service_code,
                            arrival_at=arrival_at,
                            eta=arrival_at - reference,
                        )
                    )
    return MetroArrivals(observed_at=_from_millis(response.timestamp), reference_time=reference, arrivals=arrivals)


def _itinerary_labels(itinerary: Itinerary) -> tuple[str, str]:
    legs = [leg for leg in itinerary.legs if leg.mode != TransitMode.WALK.value]
    if not legs:
        legs = itinerary.legs
    labels: list[str] = []
    descriptions: list[str] = []
    for leg in legs:
        label = leg.route or leg.mode.replace("_", " ").title()
        labels.append(label)
        from_name = leg.from_.name or f"{leg.from_.lat:.5f},{leg.from_.lon:.5f}"
        to_name = leg.to.name or f"{leg.to.lat:.5f},{leg.to.lon:.5f}"
        descriptions.append(f"{label} ({from_name} - {to_name})")
    return ", ".join(labels) or "Route", ", ".join(descriptions) or "Route"


def summarize_plan(response: PlannerResponse) -> PlannerSummary:
    """Summarize a successful plan, preserving unknown metrics and independent leg copies."""
    if response.error is not None:
        raise ResponseValidationError("Cannot summarize a planner error response")
    if response.plan is None:
        raise ResponseValidationError("Cannot summarize a planner response without a plan")
    itineraries: list[ItinerarySummary] = []
    for itinerary in response.plan.itineraries:
        overview, description = _itinerary_labels(itinerary)
        itineraries.append(
            ItinerarySummary(
                overview=overview,
                description=description,
                departure_at=_from_millis(itinerary.start_time),
                arrival_at=_from_millis(itinerary.end_time),
                duration=timedelta(seconds=itinerary.duration),
                walk_time=timedelta(seconds=itinerary.walk_time) if itinerary.walk_time is not None else None,
                transit_time=timedelta(seconds=itinerary.transit_time) if itinerary.transit_time is not None else None,
                waiting_time=timedelta(seconds=itinerary.waiting_time) if itinerary.waiting_time is not None else None,
                walk_distance=itinerary.walk_distance,
                transfers=itinerary.transfers,
                legs=[leg.model_copy(deep=True) for leg in itinerary.legs],
            )
        )
    return PlannerSummary(
        plan_date=_from_millis(response.plan.date),
        origin=response.plan.from_.model_copy(deep=True),
        destination=response.plan.to.model_copy(deep=True),
        itineraries=itineraries,
    )


def summarize_lines(response: LinesResponse) -> list[LineInfo]:
    """Create line views; geometries and collection metadata remain on the response."""
    return [
        LineInfo(
            line_id=feature.properties.line_id,
            line_code=feature.properties.line_code,
            line_name=feature.properties.line_name,
            operator_name=feature.properties.operator_name,
            transport_type_name=feature.properties.transport_type_name,
            line_origin=feature.properties.line_origin,
            line_destination=feature.properties.line_destination,
            color=feature.properties.line_color,
        )
        for feature in response.features
    ]


def summarize_bus_routes(response: BusRoutesResponse | BusRoutesConsolidatedResponse) -> list[BusRouteInfo]:
    """Create bus-route views without modifying the original collection or geometry."""
    return [
        BusRouteInfo(
            route_id=feature.properties.route_id,
            line_code=feature.properties.line_code,
            origin_name=feature.properties.origin_name,
            destination_name=feature.properties.destination_name,
            route_color=feature.properties.route_color,
        )
        for feature in response.features
    ]
