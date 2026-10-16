"""Domain views produced by the independent summary helpers."""

from datetime import datetime, timedelta

from pytmb.models._base import DomainModel
from pytmb.models.planner import Leg, Place


class BusArrival(DomainModel):
    line_code: int | str
    line_name: str
    destination: str
    route_code: str
    direction_id: int
    operator_id: int
    transit_namespace: str
    stop_code: str
    stop_name: str
    bus_id: int | None
    arrival_at: datetime
    eta: timedelta
    ramp_status: str | None

    @property
    def eta_minutes(self) -> int:
        return self.eta // timedelta(minutes=1)


class BusArrivals(DomainModel):
    observed_at: datetime
    reference_time: datetime
    arrivals: list[BusArrival]


class MetroArrival(DomainModel):
    line_code: int
    line_name: str
    line_color: str
    destination: str
    route_code: str
    direction_id: int
    station_code: int
    track: int
    service_code: str
    arrival_at: datetime
    eta: timedelta

    @property
    def eta_minutes(self) -> int:
        return self.eta // timedelta(minutes=1)


class MetroArrivals(DomainModel):
    observed_at: datetime
    reference_time: datetime
    arrivals: list[MetroArrival]


class ItinerarySummary(DomainModel):
    overview: str
    description: str
    departure_at: datetime
    arrival_at: datetime
    duration: timedelta
    walk_time: timedelta | None
    transit_time: timedelta | None
    waiting_time: timedelta | None
    walk_distance: float | None
    transfers: int | None
    legs: list[Leg]

    @property
    def duration_seconds(self) -> float:
        return self.duration.total_seconds()

    @property
    def duration_minutes(self) -> float:
        return self.duration / timedelta(minutes=1)


class PlannerSummary(DomainModel):
    plan_date: datetime
    origin: Place
    destination: Place
    itineraries: list[ItinerarySummary]
