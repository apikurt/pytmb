import pytest

from pytmb.models import Itinerary, PlannerResponse
from pytmb.summaries import summarize_plan


def test_transit_summary_preserves_route_labels_and_seconds(planner_payload):
    itinerary = Itinerary.model_validate(planner_payload["plan"]["itineraries"][0])

    summary = summarize_plan(PlannerResponse.model_validate(planner_payload)).itineraries[0]

    assert summary.overview == "H10"
    assert summary.description == "H10 (Origin - Destination)"
    assert summary.duration_minutes == 10
    assert summary.duration_seconds == 600
    assert "10.0min" in str(itinerary)
    assert "10.0min" in str(itinerary.legs[0])


def test_walking_only_summary_is_meaningful_without_modifying_the_itinerary(planner_payload):
    payload = planner_payload["plan"]["itineraries"][0]
    payload["legs"][0]["mode"] = "WALK"
    payload["legs"][0].pop("route")
    response = PlannerResponse.model_validate(planner_payload)
    before = response.model_dump()

    summary = summarize_plan(response).itineraries[0]

    assert summary.overview == "Walk"
    assert summary.description == "Walk (Origin - Destination)"
    assert response.model_dump() == before


@pytest.mark.parametrize(("duration", "label"), [(0, "0.0min"), (None, "?min")])
def test_zero_and_unknown_leg_durations_are_distinct(planner_payload, duration, label):
    itinerary = Itinerary.model_validate(planner_payload["plan"]["itineraries"][0])
    itinerary.legs[0].duration = duration

    assert label in str(itinerary.legs[0])


def test_unnamed_walking_places_use_coordinates(planner_payload):
    payload = planner_payload["plan"]["itineraries"][0]
    leg = payload["legs"][0]
    leg["mode"] = "WALK"
    leg.pop("route")
    leg["from"].pop("name")
    leg["to"].pop("name")

    summary = summarize_plan(PlannerResponse.model_validate(planner_payload)).itineraries[0]

    assert summary.description == "Walk (41.40000,2.18000 - 41.41000,2.16000)"
