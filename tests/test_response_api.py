from copy import deepcopy

import pytest

from pytmb import BusClient, MetroClient, PlannerClient, TMBClient, TransitClient
from pytmb.models import (
    BusEtaResponse,
    BusRoutesConsolidatedResponse,
    BusRoutesResponse,
    LinesResponse,
    MetroEtaResponse,
    PlannerResponse,
)
from pytmb.summaries import summarize_bus, summarize_bus_routes, summarize_lines, summarize_metro, summarize_plan


@pytest.mark.parametrize(
    ("client_type", "method", "args", "options", "payload_name", "response_type", "path"),
    [
        (BusClient, "fetch_eta", ("1234",), {}, "bus_payload", BusEtaResponse, "itransit/bus/parades/1234"),
        (MetroClient, "fetch_eta", ([123, 456],), {}, "metro_payload", MetroEtaResponse, "itransit/metro/estacions"),
        (
            PlannerClient, "fetch_plan", ((41.4, 2.18), (41.41, 2.16)), {},
            "planner_payload", PlannerResponse, "planner/plan",
        ),
        (TransitClient, "fetch_lines", ("bus",), {"srs_name": 4326}, "lines_payload", LinesResponse, "transit/linies/bus"),
        (
            TransitClient, "fetch_bus_routes", (10,), {"srs_name": "25831"},
            "routes_payload", BusRoutesResponse, "transit/linies/bus/10/recs",
        ),
        (
            TransitClient, "fetch_consolidated_bus_routes", (10,), {},
            "routes_payload", BusRoutesConsolidatedResponse, "transit/linies/bus/10/recs/cons",
        ),
    ],
)
def test_canonical_methods_return_one_response_type_and_use_existing_endpoints(
    request, respond, http_get, client_type, method, args, options, payload_name, response_type, path
):
    respond(request.getfixturevalue(payload_name))

    with client_type("dummy-id", "dummy-key") as client:
        result = getattr(client, method)(*args, **options)

    assert isinstance(result, response_type)
    http_get.assert_called_once()
    assert http_get.call_args.args[0] == f"https://api.tmb.cat/v1/{path}"
    if "srs_name" in options:
        assert http_get.call_args.kwargs["params"]["srsName"] == f"EPSG:{options['srs_name']}"


@pytest.mark.parametrize("kind", ["bus", "metro"])
def test_canonical_eta_is_complete_and_multiple_views_need_no_extra_http(
    respond, http_get, bus_payload, metro_payload, kind
):
    if kind == "bus":
        second = deepcopy(bus_payload["parades"][0]["linies_trajectes"][0])
        second.update(codi_linia=20, nom_linia="H20", codi_trajecte="20")
        bus_payload["parades"][0]["linies_trajectes"].append(second)
        respond(bus_payload)
        with TMBClient("dummy-id", "dummy-key") as client:
            response = client.bus.fetch_eta("1234")
        before = response.model_dump()
        first = summarize_bus(response, line="H10")
        other = summarize_bus(response, line="H20")
        assert len(response.stops[0].line_routes) == 2
    else:
        second = deepcopy(metro_payload["linies"][0])
        second.update(codi_linia=2, nom_linia="L2")
        metro_payload["linies"].append(second)
        respond(metro_payload)
        with TMBClient("dummy-id", "dummy-key") as client:
            response = client.metro.fetch_eta([123])
        before = response.model_dump()
        first = summarize_metro(response, line="L1")
        other = summarize_metro(response, line="L2")
        assert len(response.lines) == 2

    assert len(first.arrivals) == 3
    assert len(other.arrivals) == 3
    assert response.model_dump() == before
    http_get.assert_called_once()


def test_unknown_upstream_fields_are_ignored_by_the_typed_response_policy(respond, bus_payload):
    bus_payload["future_root"] = {"value": 1}
    bus_payload["parades"][0]["future_stop"] = "extra"
    bus_payload["parades"][0]["linies_trajectes"][0]["propers_busos"][0]["future_bus"] = True
    respond(bus_payload)

    with BusClient("dummy-id", "dummy-key") as client:
        response = client.fetch_eta("1234")

    serialized = response.model_dump(by_alias=True)
    assert response.timestamp == bus_payload["timestamp"]
    assert "future_root" not in serialized
    assert "future_stop" not in serialized["parades"][0]
    assert "future_bus" not in serialized["parades"][0]["linies_trajectes"][0]["propers_busos"][0]


def test_plan_can_be_summarized_after_client_closure(respond, http_get, planner_payload):
    respond(planner_payload)

    with PlannerClient("dummy-id", "dummy-key") as client:
        response = client.fetch_plan((41.4, 2.18), (41.41, 2.16))

    assert response.plan is not None
    assert response.plan.itineraries[0].duration == 600
    assert summarize_plan(response).itineraries[0].overview == "H10"
    http_get.assert_called_once()


@pytest.mark.parametrize("kind", ["bus", "metro"])
def test_canonical_eta_fetch_keeps_past_predictions(respond, bus_payload, metro_payload, kind):
    if kind == "bus":
        respond(bus_payload)
        with BusClient("dummy-id", "dummy-key") as client:
            response = client.fetch_eta("1234")
        predictions = response.stops[0].line_routes[0].upcoming_buses
        view = summarize_bus(response)
    else:
        respond(metro_payload)
        with MetroClient("dummy-id", "dummy-key") as client:
            response = client.fetch_eta([123])
        predictions = response.lines[0].stations[0].line_routes[0].upcoming_trains
        view = summarize_metro(response)

    assert len(predictions) == 4
    assert len(view.arrivals) == 3
    assert view.reference_time == view.observed_at


def test_line_summaries_are_independent_of_the_response_and_geometry(respond, http_get, lines_payload):
    respond(lines_payload)

    with TransitClient("dummy-id", "dummy-key") as client:
        response = client.fetch_lines("bus")
    before = response.model_dump()
    view = summarize_lines(response)
    view[0].line_name = "Changed view"

    assert response.features[0].properties.line_name == "H10"
    assert response.features[0].geometry.coordinates == [(2.18, 41.4), (2.16, 41.41)]
    assert response.timestamp == "2026-10-16T10:00:00Z"
    assert response.total_features == 1
    assert response.number_returned == 1
    assert response.model_dump() == before
    http_get.assert_called_once()


@pytest.mark.parametrize("consolidated", [False, True])
def test_bus_route_summaries_work_with_both_collection_types(respond, routes_payload, consolidated):
    respond(routes_payload)
    with TransitClient("dummy-id", "dummy-key") as client:
        response = client.fetch_consolidated_bus_routes(10) if consolidated else client.fetch_bus_routes(10)
    before = response.model_dump()

    view = summarize_bus_routes(response)

    assert view[0].route_id == 1000
    assert view[0].origin_name == "Origin"
    assert view[0].destination_name == "Destination"
    assert response.model_dump() == before


def test_empty_metro_station_selection_fails_before_http(http_get):
    with MetroClient("dummy-id", "dummy-key") as client:
        with pytest.raises(ValueError, match="At least one station code"):
            client.fetch_eta([])

    http_get.assert_not_called()
