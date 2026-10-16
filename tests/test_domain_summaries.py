from copy import deepcopy
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from pytmb import ResponseValidationError
from pytmb.models import BusEtaResponse, MetroEtaResponse, PlannerResponse
from pytmb.summaries import filter_bus, filter_metro, summarize_bus, summarize_metro, summarize_plan


OBSERVED = datetime(1970, 1, 1, 0, 16, 40, tzinfo=timezone.utc)


@pytest.fixture(params=["bus", "metro"])
def arrivals_case(request, bus_payload, metro_payload):
    if request.param == "bus":
        return SimpleNamespace(
            response=BusEtaResponse.model_validate(bus_payload),
            summarize=summarize_bus,
            line="H10",
        )
    return SimpleNamespace(
        response=MetroEtaResponse.model_validate(metro_payload),
        summarize=summarize_metro,
        line="L1",
    )


def test_arrival_views_preserve_snapshot_and_exact_arrival_times(arrivals_case):
    view = arrivals_case.summarize(arrivals_case.response)

    assert view.observed_at == OBSERVED
    assert view.reference_time == OBSERVED
    assert [arrival.eta_minutes for arrival in view.arrivals] == [0, 0, 1]
    assert view.arrivals[1].arrival_at == OBSERVED + timedelta(milliseconds=59999)
    assert view.arrivals[1].eta == timedelta(milliseconds=59999)
    assert view.arrivals[2].arrival_at == OBSERVED + timedelta(minutes=1)


def test_arrival_views_are_deterministic_and_do_not_modify_the_response(arrivals_case):
    before = arrivals_case.response.model_dump()

    first = arrivals_case.summarize(arrivals_case.response, line=f" {arrivals_case.line.lower()} ")
    second = arrivals_case.summarize(arrivals_case.response, line=arrivals_case.line)

    assert first.model_dump() == second.model_dump()
    assert arrivals_case.response.model_dump() == before
    first.arrivals[0].destination = "Changed view"
    assert arrivals_case.response.model_dump() == before


def test_explicit_reference_time_changes_etas_without_changing_observation_time(arrivals_case):
    reference = OBSERVED + timedelta(seconds=30)

    view = arrivals_case.summarize(arrivals_case.response, at=reference)

    assert view.reference_time == reference
    assert view.observed_at == OBSERVED
    assert [arrival.eta for arrival in view.arrivals] == [timedelta(milliseconds=29999), timedelta(seconds=30)]


def test_timezone_aware_reference_is_normalized_to_utc(arrivals_case):
    at = OBSERVED.astimezone(timezone(timedelta(hours=2)))

    view = arrivals_case.summarize(arrivals_case.response, at=at)

    assert view.reference_time == OBSERVED
    assert view.reference_time.tzinfo is timezone.utc
    assert [arrival.eta_minutes for arrival in view.arrivals] == [0, 0, 1]


def test_reference_time_retains_submillisecond_precision(arrivals_case):
    view = arrivals_case.summarize(arrivals_case.response, at=OBSERVED + timedelta(microseconds=1))

    assert [arrival.eta_minutes for arrival in view.arrivals] == [0, 0]
    assert view.arrivals[-1].eta == timedelta(seconds=60, microseconds=-1)


@pytest.mark.parametrize("at", [datetime(2026, 1, 1), "now", 1000])
def test_invalid_reference_time_is_rejected(arrivals_case, at):
    with pytest.raises(ValueError, match="timezone-aware datetime"):
        arrivals_case.summarize(arrivals_case.response, at=at)


def test_past_arrivals_can_be_retained_explicitly(arrivals_case):
    view = arrivals_case.summarize(arrivals_case.response, include_past=True)

    assert [arrival.eta_minutes for arrival in view.arrivals] == [-1, 0, 0, 1]
    assert view.arrivals[0].eta == timedelta(seconds=-1)


def test_empty_filtered_view_keeps_observation_and_reference_metadata(arrivals_case):
    view = arrivals_case.summarize(arrivals_case.response, line="nonexistent")

    assert view.arrivals == []
    assert view.observed_at == OBSERVED
    assert view.reference_time == OBSERVED


def test_summary_models_round_trip_datetimes_and_timedeltas(arrivals_case):
    view = arrivals_case.summarize(arrivals_case.response)

    restored = type(view).model_validate_json(view.model_dump_json())

    assert restored.model_dump() == view.model_dump()


def test_bus_view_preserves_identity_and_unknown_accessibility(bus_payload):
    view = summarize_bus(BusEtaResponse.model_validate(bus_payload))
    arrival = view.arrivals[0]

    assert arrival.bus_id == 2
    assert arrival.stop_code == "1234"
    assert arrival.stop_name == "Test stop"
    assert arrival.operator_id == 1
    assert arrival.transit_namespace == "bus"
    assert arrival.direction_id == 1
    assert arrival.route_code == "10"
    assert arrival.ramp_status is None


def test_bus_view_keeps_known_accessibility_value(bus_payload):
    bus_payload["parades"][0]["linies_trajectes"][0]["propers_busos"][1]["info_bus"] = {
        "accessibilitat": {"estat_rampa": "working"}
    }

    view = summarize_bus(BusEtaResponse.model_validate(bus_payload))

    assert view.arrivals[0].ramp_status == "working"
    assert view.arrivals[1].ramp_status is None


def test_metro_view_preserves_track_direction_and_service(metro_payload):
    view = summarize_metro(MetroEtaResponse.model_validate(metro_payload))
    arrival = view.arrivals[0]

    assert arrival.track == 1
    assert arrival.direction_id == 1
    assert arrival.station_code == 123
    assert arrival.service_code == "2"
    assert arrival.route_code == "1"
    assert arrival.line_name == "L1"


def test_bus_filter_keeps_empty_stops_and_returns_independent_nested_objects(bus_payload):
    original = BusEtaResponse.model_validate(bus_payload)
    before = original.model_dump()

    matching = filter_bus(original, " h10 ")
    empty = filter_bus(original, "nonexistent")
    matching.stops[0].line_routes[0].upcoming_buses[0].bus_id = 999

    assert empty.timestamp == original.timestamp
    assert len(empty.stops) == 1
    assert empty.stops[0].line_routes == []
    assert original.model_dump() == before


def test_metro_filter_returns_independent_nested_objects(metro_payload):
    second = deepcopy(metro_payload["linies"][0])
    second.update(codi_linia=2, nom_linia="L2")
    metro_payload["linies"].append(second)
    original = MetroEtaResponse.model_validate(metro_payload)
    before = original.model_dump()

    matching = filter_metro(original, " l1 ")
    matching.lines[0].stations[0].track = 2

    assert len(matching.lines) == 1
    assert filter_metro(original, "nonexistent").lines == []
    assert original.model_dump() == before


def test_planner_view_preserves_unknown_metrics(planner_payload):
    itinerary = planner_payload["plan"]["itineraries"][0]
    for key in ["transitTime", "waitingTime", "walkDistance", "transfers"]:
        itinerary.pop(key)
    response = PlannerResponse.model_validate(planner_payload)

    view = summarize_plan(response)
    assert response.plan is not None
    route = view.itineraries[0]

    assert route.walk_time is None
    assert route.transit_time is None
    assert route.waiting_time is None
    assert route.walk_distance is None
    assert route.transfers is None
    assert "transfers=?" in str(response.plan.itineraries[0])


def test_planner_view_distinguishes_known_zero_from_unknown(planner_payload):
    planner_payload["plan"]["itineraries"][0].update(walkTime=0, transitTime=0, waitingTime=0, walkDistance=0, transfers=0)

    route = summarize_plan(PlannerResponse.model_validate(planner_payload)).itineraries[0]

    assert route.walk_time == timedelta(0)
    assert route.transit_time == timedelta(0)
    assert route.waiting_time == timedelta(0)
    assert route.walk_distance == 0
    assert route.transfers == 0


def test_planner_view_retains_fractional_distance_and_duration_precision(planner_payload):
    planner_payload["plan"]["itineraries"][0].update(duration=605, endTime=1605000, walkDistance=123.456)

    view = summarize_plan(PlannerResponse.model_validate(planner_payload))
    route = view.itineraries[0]

    assert view.plan_date == OBSERVED
    assert route.departure_at == OBSERVED
    assert route.arrival_at == OBSERVED + timedelta(seconds=605)
    assert route.duration == timedelta(seconds=605)
    assert route.duration_seconds == 605
    assert route.duration_minutes == pytest.approx(605 / 60)
    assert route.walk_distance == 123.456


def test_planner_view_retains_structured_legs_and_copies_nested_data(planner_payload):
    leg = planner_payload["plan"]["itineraries"][0]["legs"][0]
    leg.update(routeId="route-10", tripId="trip-001", agencyId="TMB", legGeometry={"points": "encoded", "length": 2})
    leg["from"]["stopId"] = "stop-1234"
    response = PlannerResponse.model_validate(planner_payload)
    before = response.model_dump()

    view = summarize_plan(response)
    copied_leg = view.itineraries[0].legs[0]

    assert copied_leg.route_id == "route-10"
    assert copied_leg.trip_id == "trip-001"
    assert copied_leg.agency_id == "TMB"
    assert copied_leg.from_.stop_id == "stop-1234"
    assert copied_leg.leg_geometry is not None
    assert copied_leg.leg_geometry.points == "encoded"
    copied_leg.leg_geometry.points = "changed"
    copied_leg.from_.name = "Changed leg"
    view.origin.name = "Changed origin"
    assert response.model_dump() == before


def test_successful_empty_plan_keeps_metadata(planner_payload):
    planner_payload["plan"]["itineraries"] = []

    view = summarize_plan(PlannerResponse.model_validate(planner_payload))

    assert view.itineraries == []
    assert view.plan_date == OBSERVED
    assert view.origin.name == "Origin"
    assert view.destination.name == "Destination"


@pytest.mark.parametrize("payload", [{}, {"error": {"msg": "dummy-key"}}])
def test_invalid_or_error_planner_responses_are_not_hidden_as_empty_views(payload):
    with pytest.raises(ResponseValidationError) as caught:
        summarize_plan(PlannerResponse.model_validate(payload))

    assert "dummy-key" not in str(caught.value)
