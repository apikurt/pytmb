from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class Place(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    name: Optional[str] = None
    lat: float
    lon: float
    orig: Optional[str] = None
    stop_id: Optional[str] = Field(default=None, alias="stopId")
    stop_code: Optional[str] = Field(default=None, alias="stopCode")
    vertex_type: Optional[str] = Field(default=None, alias="vertexType")

    def __repr__(self) -> str:
        return f"Place(name={self.name}, lat={self.lat}, lon={self.lon})"


class LegGeometry(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    points: str
    length: int


class Step(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    # Distance can be fractional (meters), so use float
    distance: Optional[float] = None
    relative_direction: Optional[str] = Field(default=None, alias="relativeDirection")
    street_name: Optional[str] = Field(default=None, alias="streetName")
    absolute_direction: Optional[str] = Field(default=None, alias="absoluteDirection")
    exit: Optional[str] = None
    stay_on: Optional[bool] = Field(default=None, alias="stayOn")
    area: Optional[bool] = None
    bogus_name: Optional[bool] = Field(default=None, alias="bogusName")
    lon: Optional[float] = None
    lat: Optional[float] = None
    alerts: Optional[List[Dict[str, Any]]] = None
    # OTP returns elevation profile as a comma-separated string; keep raw
    elevation: Optional[str] = None


class Leg(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    mode: str
    start_time: int = Field(alias="startTime")
    end_time: int = Field(alias="endTime")
    distance: float
    departure_delay: Optional[int] = Field(default=None, alias="departureDelay")
    arrival_delay: Optional[int] = Field(default=None, alias="arrivalDelay")
    real_time: Optional[bool] = Field(default=None, alias="realTime")
    is_non_exact_frequency: Optional[bool] = Field(default=None, alias="isNonExactFrequency")
    headway: Optional[int] = None
    pathway: Optional[bool] = None
    transit_leg: Optional[bool] = Field(default=None, alias="transitLeg")

    route: Optional[str] = None
    route_id: Optional[str] = Field(default=None, alias="routeId")
    route_short_name: Optional[str] = Field(default=None, alias="routeShortName")
    route_long_name: Optional[str] = Field(default=None, alias="routeLongName")
    agency_name: Optional[str] = Field(default=None, alias="agencyName")
    agency_url: Optional[str] = Field(default=None, alias="agencyUrl")
    agency_time_zone_offset: Optional[int] = Field(default=None, alias="agencyTimeZoneOffset")
    route_color: Optional[str] = Field(default=None, alias="routeColor")
    route_type: Optional[int] = Field(default=None, alias="routeType")
    route_text_color: Optional[str] = Field(default=None, alias="routeTextColor")
    interline_with_previous_leg: Optional[bool] = Field(default=None, alias="interlineWithPreviousLeg")
    trip_short_name: Optional[str] = Field(default=None, alias="tripShortName")
    trip_block_id: Optional[str] = Field(default=None, alias="tripBlockId")
    headsign: Optional[str] = None
    agency_id: Optional[str] = Field(default=None, alias="agencyId")
    trip_id: Optional[str] = Field(default=None, alias="tripId")
    service_date: Optional[str] = Field(default=None, alias="serviceDate")

    from_: Place = Field(alias="from")
    to: Place

    leg_geometry: Optional[LegGeometry] = Field(default=None, alias="legGeometry")
    intermediate_stops: Optional[List[Place]] = Field(default=None, alias="intermediateStops")
    steps: Optional[List["Step"]] = None
    alerts: Optional[List[Dict[str, Any]]] = None
    board_rule: Optional[str] = Field(default=None, alias="boardRule")
    alight_rule: Optional[str] = Field(default=None, alias="alightRule")
    rented_bike: Optional[bool] = Field(default=None, alias="rentedBike")
    duration: Optional[int] = None


class Itinerary(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    duration: int
    start_time: int = Field(alias="startTime")
    end_time: int = Field(alias="endTime")

    walk_time: Optional[int] = Field(default=None, alias="walkTime")
    transit_time: Optional[int] = Field(default=None, alias="transitTime")
    waiting_time: Optional[int] = Field(default=None, alias="waitingTime")
    walk_distance: Optional[float] = Field(default=None, alias="walkDistance")
    generalized_cost: Optional[int] = Field(default=None, alias="generalizedCost")
    walk_limit_exceeded: Optional[bool] = Field(default=None, alias="walkLimitExceeded")
    elevation_lost: Optional[float] = Field(default=None, alias="elevationLost")
    elevation_gained: Optional[float] = Field(default=None, alias="elevationGained")

    transfers: Optional[int] = None
    fare: Optional[Dict[str, Any]] = None
    legs: List[Leg]
    too_sloped: Optional[bool] = Field(default=None, alias="tooSloped")


class Plan(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    date: int
    from_: Place = Field(alias="from")
    to: Place
    itineraries: List[Itinerary]


class PlannerError(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: Optional[int] = None
    msg: Optional[str] = None
    message: Optional[str] = None
    missing: Optional[List[str]] = None
    no_path: Optional[bool] = Field(default=None, alias="noPath")


class DebugOutput(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    precalculation_time: Optional[int] = Field(default=None, alias="precalculationTime")
    path_calculation_time: Optional[int] = Field(default=None, alias="pathCalculationTime")
    path_times: Optional[List[int]] = Field(default=None, alias="pathTimes")
    rendering_time: Optional[int] = Field(default=None, alias="renderingTime")
    total_time: Optional[int] = Field(default=None, alias="totalTime")
    timed_out: Optional[bool] = Field(default=None, alias="timedOut")


class PlannerResponse(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    plan: Optional[Plan] = None
    error: Optional[PlannerError] = None
    request_parameters: Optional[Dict[str, str]] = Field(default=None, alias="requestParameters")
    debug_output: Optional[DebugOutput] = Field(default=None, alias="debugOutput")

    def __repr__(self):
        if self.plan is not None:
            itin_count = len(self.plan.itineraries)
        else:
            itin_count = 0
        return f"PlannerResponse(plan_itineraries={itin_count}, error={self.error})"


class PlannerRouteInfo(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    overview: str
    description: str
    duration_in_minutes: int
    duration_in_seconds: int
    transit_time: int
    waiting_time: int
    walk_distance: int
    transfers: int

    def __repr__(self) -> str:
        return (
            f"PlannerRouteInfo(overview={self.overview!r}, duration_in_minutes={self.duration_in_minutes}, "
            f"transfers={self.transfers})"
        )
