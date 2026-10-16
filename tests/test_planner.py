from datetime import date, datetime, time, timezone
from importlib import import_module

import pytest

from pytmb import APIError, PlannerClient, ResponseValidationError
from pytmb.enums import TransitMode
from pytmb.models import PlannerResponse
from pytmb.summaries import summarize_plan


ORIGIN = (41.4, 2.18)
DESTINATION = (41.41, 2.16)


@pytest.fixture
def planner():
    with PlannerClient("dummy-id", "dummy-key") as client:
        yield client


@pytest.mark.parametrize("message_field", ["msg", "message"])
def test_application_errors_raise_with_upstream_details(planner, respond, message_field):
    respond({"error": {"id": 400, message_field: "Invalid request", "missing": ["fromPlace"]}})

    with pytest.raises(APIError, match="Invalid request") as caught:
        planner.fetch_plan(ORIGIN, DESTINATION)

    assert caught.value.code == 400
    assert caught.value.details["missing"] == ["fromPlace"]


def test_application_error_without_message_has_a_useful_fallback(planner, respond):
    respond({"error": {}})

    with pytest.raises(APIError, match="Planner request failed"):
        planner.fetch_plan(ORIGIN, DESTINATION)


@pytest.mark.parametrize("payload", [{}, {"plan": None}, {"requestParameters": {}}])
def test_missing_plan_is_not_a_successful_empty_result(planner, respond, payload):
    respond(payload)

    with pytest.raises(ResponseValidationError, match="neither a plan nor an error"):
        planner.fetch_plan(ORIGIN, DESTINATION)


def test_successful_empty_plan_is_preserved(planner, respond, planner_payload):
    planner_payload["plan"]["itineraries"] = []
    respond(planner_payload)

    result = planner.fetch_plan(ORIGIN, DESTINATION)

    assert isinstance(result, PlannerResponse)
    assert result.plan is not None
    assert result.plan.itineraries == []
    assert summarize_plan(result).itineraries == []


@pytest.mark.parametrize("place", [(41, 2), (41, 2.18), (-90, -180), (90.0, 180.0)])
def test_valid_numeric_coordinates_are_serialized(planner, respond, http_get, planner_payload, place):
    respond(planner_payload)

    planner.fetch_plan(place, place)

    params = http_get.call_args.kwargs["params"]
    assert params["fromPlace"] == f"{place[0]},{place[1]}"
    assert params["toPlace"] == f"{place[0]},{place[1]}"


@pytest.mark.parametrize("parameter", ["from_place", "to_place"])
@pytest.mark.parametrize(
    "place",
    [
        (91.0, 2.0),
        (41.0, -181.0),
        (float("nan"), 2.0),
        (41.0, float("inf")),
        (True, 2.0),
        ("41.0", 2.0),
        (10**1000, 2),
        [41.0, 2.0],
        (41.0,),
        None,
    ],
)
def test_invalid_coordinates_fail_before_http(planner, http_get, parameter, place):
    places = {"from_place": ORIGIN, "to_place": DESTINATION, parameter: place}

    with pytest.raises(ValueError, match=parameter):
        planner.fetch_plan(**places)

    http_get.assert_not_called()


@pytest.mark.parametrize("distance", [-1, float("nan"), float("inf"), True, "100", 10**1000])
def test_invalid_walking_distance_fails_before_http(planner, http_get, distance):
    with pytest.raises(ValueError, match="max_walk_distance"):
        planner.fetch_plan(ORIGIN, DESTINATION, max_walk_distance=distance)

    http_get.assert_not_called()


@pytest.mark.parametrize("mode", [[], ["BUS"], [TransitMode.BUS, "WALK"], "BUS", True])
def test_invalid_modes_fail_before_http(planner, http_get, mode):
    with pytest.raises(ValueError, match="mode"):
        planner.fetch_plan(ORIGIN, DESTINATION, mode=mode)

    http_get.assert_not_called()


@pytest.mark.parametrize(
    ("mode", "wire_value"),
    [(None, "TRANSIT,WALK"), (TransitMode.BUS, "BUS"), ([TransitMode.SUBWAY, TransitMode.WALK], "SUBWAY,WALK")],
)
def test_modes_and_optional_parameters_are_serialized(
    planner, respond, http_get, planner_payload, mode, wire_value
):
    respond(planner_payload)

    planner.fetch_plan(
        ORIGIN,
        DESTINATION,
        mode=mode,
        arrive_by=True,
        max_walk_distance=0,
        show_intermediate_stops=False,
    )

    params = http_get.call_args.kwargs["params"]
    assert params["mode"] == wire_value
    assert params["arriveBy"] == "true"
    assert params["maxWalkDistance"] == 0
    assert params["showIntermediateStops"] == "false"


@pytest.mark.parametrize(
    ("instant", "expected_date", "expected_time"),
    [
        (datetime(2026, 1, 1, 22, 30, tzinfo=timezone.utc), "01-01-2026", "11:30pm"),
        (datetime(2026, 7, 1, 22, 30, tzinfo=timezone.utc), "07-02-2026", "12:30am"),
    ],
)
def test_defaults_use_barcelona_time(
    planner, respond, http_get, planner_payload, monkeypatch, instant, expected_date, expected_time
):
    class FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return instant.astimezone(tz) if tz is not None else instant.replace(tzinfo=None)

    monkeypatch.setattr(import_module("pytmb.planner"), "datetime", FrozenDatetime)
    respond(planner_payload)

    planner.fetch_plan(ORIGIN, DESTINATION)

    params = http_get.call_args.kwargs["params"]
    assert (params["date"], params["time"]) == (expected_date, expected_time)


@pytest.mark.parametrize(
    ("day", "clock", "expected_date", "expected_time"),
    [
        (date(2026, 1, 1), time(23, 30), "01-01-2026", "11:30pm"),
        (date(2026, 1, 1), time(23, 30, tzinfo=timezone.utc), "01-02-2026", "12:30am"),
        (date(2026, 7, 1), time(23, 30, tzinfo=timezone.utc), "07-02-2026", "01:30am"),
    ],
)
def test_explicit_times_convert_to_barcelona_including_date_rollover(
    planner, respond, http_get, planner_payload, day, clock, expected_date, expected_time
):
    respond(planner_payload)

    planner.fetch_plan(ORIGIN, DESTINATION, date=day, time=clock)

    params = http_get.call_args.kwargs["params"]
    assert (params["date"], params["time"]) == (expected_date, expected_time)
