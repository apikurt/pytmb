"""Offline replay of sanitized responses captured from the real TMB API."""

import json
from datetime import date, datetime, time, timedelta
from pathlib import Path

import pytest

from pytmb import HTTPError, TMBClient, TransitMode
from pytmb.models import (
    BusEtaResponse,
    BusRoutesConsolidatedResponse,
    BusRoutesResponse,
    LineString,
    LinesResponse,
    MetroEtaResponse,
    PlannerResponse,
)
from pytmb.summaries import summarize_bus, summarize_metro, summarize_plan


FIXTURES = Path(__file__).parent / "fixtures"
MODELS = {
    "bus_eta": BusEtaResponse,
    "metro_eta": MetroEtaResponse,
    "planner": PlannerResponse,
    "lines": LinesResponse,
    "bus_routes": BusRoutesResponse,
    "bus_routes_consolidated": BusRoutesConsolidatedResponse,
}
METADATA = [(path.stem.removesuffix(".meta"), json.loads(path.read_text(encoding="utf-8")))
            for path in sorted(FIXTURES.glob("*.meta.json"))]
CONTRACTS = [(name, metadata) for name, metadata in METADATA if metadata["model"] is not None]
SUCCESSFUL = [(name, metadata) for name, metadata in CONTRACTS if metadata["outcome"] == "success"]


def load_payload(metadata):
    name = metadata["payload_file"]
    assert Path(name).name == name
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def load_named(name):
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize(("name", "metadata"), METADATA, ids=[name for name, _ in METADATA])
def test_capture_provenance_is_complete_and_omits_authentication(name, metadata):
    assert metadata["provenance"] == "live_api_capture"
    assert datetime.fromisoformat(metadata["captured_at"]).utcoffset() == timedelta(0)
    assert metadata["method"] == "GET"
    assert metadata["api_version"] == "v1"
    assert "?" not in metadata["endpoint"]
    assert metadata["payload_file"] == f"{name}.json"
    assert not {"app_id", "app_key"} & metadata["query"].keys()
    assert metadata["model"] is None or metadata["model"] in MODELS
    assert isinstance(load_payload(metadata), dict)


@pytest.mark.parametrize(("name", "metadata"), SUCCESSFUL, ids=[name for name, _ in SUCCESSFUL])
def test_live_response_contract_and_cached_round_trip(name, metadata):
    model = MODELS[metadata["model"]]
    response = model.model_validate(load_payload(metadata))

    assert model.model_validate(response.model_dump()).model_dump() == response.model_dump()
    assert model.model_validate_json(response.model_dump_json(by_alias=True)).model_dump() == response.model_dump()


def fetch_recorded_response(client, metadata):
    endpoint = metadata["endpoint"]
    query = metadata["query"]
    model = metadata["model"]
    if model == "bus_eta":
        return client.bus.fetch_eta(endpoint.rsplit("/", 1)[-1])
    if model == "metro_eta":
        return client.metro.fetch_eta([int(code) for code in query["estacions"].split(",")])
    if model == "planner":
        origin = query["fromPlace"].split(",")
        destination = query["toPlace"].split(",")
        month, day, year = (int(value) for value in query["date"].split("-"))
        clock = query["time"]
        hour, minute = clock[:-2].split(":")
        return client.planner.fetch_plan(
            (float(origin[0]), float(origin[1])),
            (float(destination[0]), float(destination[1])),
            date=date(year, month, day),
            time=time(int(hour) % 12 + (12 if clock.endswith("pm") else 0), int(minute)),
            mode=[TransitMode(value) for value in query["mode"].split(",")],
            arrive_by=query["arriveBy"] == "true",
            show_intermediate_stops=query.get("showIntermediateStops") == "true"
            if "showIntermediateStops" in query else None,
        )
    if model == "lines":
        # Recorded filters select representative data without changing its response envelope.
        return client.transit.fetch_lines(endpoint.rsplit("/", 1)[-1], srs_name=query.get("srsName"))
    line_code = int(endpoint.split("/")[3])
    if model == "bus_routes":
        return client.transit.fetch_bus_routes(line_code, srs_name=query.get("srsName"))
    return client.transit.fetch_consolidated_bus_routes(line_code, srs_name=query.get("srsName"))


@pytest.mark.parametrize(("name", "metadata"), SUCCESSFUL, ids=[name for name, _ in SUCCESSFUL])
def test_public_clients_decode_real_responses_offline(name, metadata, http_get, make_response):
    response = make_response(
        load_payload(metadata), status=metadata["status_code"], headers=metadata["response_headers"]
    )
    http_get.side_effect = None
    http_get.return_value = response

    with TMBClient("dummy-id", "dummy-key", max_retries=0) as client:
        result = fetch_recorded_response(client, metadata)

    assert isinstance(result, MODELS[metadata["model"]])
    assert http_get.call_args.args[0] == f"https://api.tmb.cat/v1/{metadata['endpoint']}"
    http_get.assert_called_once()
    response.close.assert_called_once()


def test_amb_predictions_accept_alphanumeric_codes_and_missing_vehicle_ids():
    payload = load_named("bus_eta")
    response = BusEtaResponse.model_validate(payload)

    arrivals = summarize_bus(response, line=" n16 ")

    assert response.stops[0].stop_code == "108"
    assert response.stops[0].line_routes[0].line_code == "N16"
    assert len(arrivals.arrivals) == 2
    assert all(arrival.line_code == "N16" and arrival.transit_namespace == "amb" for arrival in arrivals.arrivals)
    assert all(arrival.bus_id is None for arrival in arrivals.arrivals)
    assert all("id_bus" not in bus for route in payload["parades"][0]["linies_trajectes"] for bus in route["propers_busos"])


def test_real_empty_responses_remain_successful_and_keep_metadata():
    bus = BusEtaResponse.model_validate(load_named("bus_eta_empty"))
    metro = MetroEtaResponse.model_validate(load_named("metro_eta_empty"))
    lines = LinesResponse.model_validate(load_named("bus_lines_empty"))
    plan = PlannerResponse.model_validate(load_named("planner_empty"))

    assert summarize_bus(bus).arrivals == []
    assert summarize_metro(metro).arrivals == []
    assert lines.features == [] and lines.total_features == 0
    summary = summarize_plan(plan)
    assert summary.itineraries == []
    assert summary.origin.lat == pytest.approx(41.37552)
    assert summary.destination.lat == 0


def test_real_metro_off_hours_snapshot_preserves_station_and_track_metadata():
    response = MetroEtaResponse.model_validate(load_named("metro_eta"))

    assert response.lines[0].line_name == "L1"
    assert {station.station_code for station in response.lines[0].stations} == {115, 123}
    assert {station.track for station in response.lines[0].stations} == {1, 2}
    assert summarize_metro(response).arrivals == []


def test_running_metro_predictions_preserve_service_route_track_and_direction():
    response = MetroEtaResponse.model_validate(load_named("metro_eta_running"))
    before = response.model_dump()

    snapshot = summarize_metro(response, line=" l1 ")

    assert len(snapshot.arrivals) == 7
    assert {(arrival.station_code, arrival.track, arrival.direction_id) for arrival in snapshot.arrivals} == {
        (115, 1, 1), (115, 2, 2), (123, 1, 1), (123, 2, 2),
    }
    assert {arrival.route_code for arrival in snapshot.arrivals} == {"0011", "0012"}
    assert {arrival.service_code for arrival in snapshot.arrivals} == {"101", "103", "125", "129", "130", "133", "135"}
    assert all(arrival.eta > timedelta(0) for arrival in snapshot.arrivals)
    assert response.model_dump() == before


def test_operating_bus_snapshot_preserves_numeric_tmb_ids_and_amb_unknowns():
    response = BusEtaResponse.model_validate(load_named("bus_eta_operating"))
    before = response.model_dump()

    tmb = summarize_bus(response, line=" h12 ")
    amb = summarize_bus(response, line=" l72 ")

    assert len(tmb.arrivals) == 2
    assert {arrival.bus_id for arrival in tmb.arrivals} == {8531, 8570}
    assert all(arrival.line_code == 212 and isinstance(arrival.line_code, int) for arrival in tmb.arrivals)
    assert all(arrival.line_name == "H12" and arrival.transit_namespace == "bus" for arrival in tmb.arrivals)
    assert all(arrival.operator_id == 2 and arrival.ramp_status == "SENSE_INCIDENCIA" for arrival in tmb.arrivals)
    assert len(amb.arrivals) == 2
    assert all(arrival.line_code == "L72" and arrival.transit_namespace == "amb" for arrival in amb.arrivals)
    assert all(arrival.bus_id is None and arrival.ramp_status is None for arrival in amb.arrivals)
    assert response.model_dump() == before


def test_real_planner_views_include_walking_transit_and_intermediate_stops():
    transit = summarize_plan(PlannerResponse.model_validate(load_named("planner_transit")))
    walking = summarize_plan(PlannerResponse.model_validate(load_named("planner_walk")))

    assert any(leg.mode == "SUBWAY" for itinerary in transit.itineraries for leg in itinerary.legs)
    assert any(leg.intermediate_stops for itinerary in transit.itineraries for leg in itinerary.legs)
    assert walking.itineraries[0].overview == "Walk"
    assert walking.itineraries[0].walk_distance == pytest.approx(387.93)
    assert walking.itineraries[0].duration == timedelta(seconds=368)


def test_real_projected_coordinates_and_crs_remain_projected():
    response = BusRoutesResponse.model_validate(load_named("bus_routes_projected"))
    geometry = response.features[0].geometry
    point = geometry.coordinates[0] if isinstance(geometry, LineString) else geometry.coordinates[0][0]

    assert response.crs is not None and "25831" in response.crs.properties.name
    assert point[0] > 180 and point[1] > 90


def test_recorded_planner_validation_failure_is_an_http_error(http_get, make_response):
    metadata = dict(CONTRACTS)["planner_invalid_mode"]
    response = make_response(load_payload(metadata), status=metadata["status_code"])
    http_get.side_effect = None
    http_get.return_value = response

    with TMBClient("dummy-id", "dummy-key", max_retries=0) as client:
        with pytest.raises(HTTPError) as caught:
            client._transport.get_model("planner/plan", PlannerResponse, params=metadata["query"])

    assert caught.value.status_code == 500
    response.json.assert_not_called()
    response.close.assert_called_once()
    http_get.assert_called_once()


def test_client_rejects_the_recorded_invalid_mode_before_sending(http_get):
    metadata = dict(CONTRACTS)["planner_invalid_mode"]
    with TMBClient("dummy-id", "dummy-key") as client:
        with pytest.raises(ValueError, match="mode"):
            client.planner.fetch_plan((41.3755204, 2.1498870), (41.403629, 2.174356), mode=metadata["query"]["mode"])
    http_get.assert_not_called()
