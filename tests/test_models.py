from copy import deepcopy

import pytest
from pydantic import TypeAdapter, ValidationError

from pytmb import ResponseValidationError, TransitClient
from pytmb.models import (
    BusEtaResponse,
    BusRoutesConsolidatedResponse,
    BusRoutesResponse,
    Geometry,
    LineString,
    LinesResponse,
    MetroEtaResponse,
    MultiLineString,
    PlannerResponse,
)
from pytmb.summaries import summarize_bus, summarize_bus_routes, summarize_lines, summarize_metro, summarize_plan


@pytest.mark.parametrize(
    ("model", "fixture_name"),
    [
        (BusEtaResponse, "bus_payload"),
        (MetroEtaResponse, "metro_payload"),
        (PlannerResponse, "planner_payload"),
        (LinesResponse, "lines_payload"),
        (BusRoutesResponse, "routes_payload"),
        (BusRoutesConsolidatedResponse, "routes_payload"),
    ],
)
def test_response_families_accept_aliases_and_names_and_ignore_new_fields(request, model, fixture_name):
    payload = deepcopy(request.getfixturevalue(fixture_name))
    payload["future_upstream_field"] = {"value": 1}

    response = model.model_validate(payload)

    assert "future_upstream_field" not in response.model_dump()
    assert model.model_validate(response.model_dump()).model_dump() == response.model_dump()
    assert model.model_validate(response.model_dump(by_alias=True)).model_dump() == response.model_dump()


@pytest.mark.parametrize("kind", ["bus", "metro", "plan", "lines", "routes"])
def test_domain_views_reject_unexpected_fields(
    kind, bus_payload, metro_payload, planner_payload, lines_payload, routes_payload
):
    if kind == "bus":
        view = summarize_bus(BusEtaResponse.model_validate(bus_payload))
    elif kind == "metro":
        view = summarize_metro(MetroEtaResponse.model_validate(metro_payload))
    elif kind == "plan":
        view = summarize_plan(PlannerResponse.model_validate(planner_payload))
    elif kind == "lines":
        view = summarize_lines(LinesResponse.model_validate(lines_payload))[0]
    else:
        view = summarize_bus_routes(BusRoutesResponse.model_validate(routes_payload))[0]
    payload = {**view.model_dump(), "mistyped_field": 1}

    with pytest.raises(ValidationError) as caught:
        type(view).model_validate(payload)

    assert caught.value.errors()[0]["type"] == "extra_forbidden"


@pytest.mark.parametrize(
    ("tag", "coordinates", "expected_type"),
    [
        ("LineString", [[2.18, 41.4], [2.16, 41.41]], LineString),
        ("MultiLineString", [[[2.18, 41.4], [2.16, 41.41]], [[2.15, 41.42], [2.14, 41.43]]], MultiLineString),
        ("LineString", [[430000.5, 4580000.25], [430010.5, 4580020.25]], LineString),
    ],
)
def test_geometry_tag_selects_the_coordinate_model_and_round_trips(tag, coordinates, expected_type):
    adapter = TypeAdapter(Geometry)
    geometry = adapter.validate_python({"type": tag, "coordinates": coordinates, "future_geometry_field": True})

    assert isinstance(geometry, expected_type)
    assert geometry.type_ == tag
    assert adapter.validate_json(adapter.dump_json(geometry, by_alias=True)) == geometry
    assert "future_geometry_field" not in geometry.model_dump()
    assert geometry.model_dump(by_alias=True)["type"] == tag


@pytest.mark.parametrize(
    "payload",
    [
        {"type": "LineString", "coordinates": [[[2.18, 41.4], [2.16, 41.41]]]},
        {"type": "MultiLineString", "coordinates": [[2.18, 41.4], [2.16, 41.41]]},
        {"type": "LineString", "coordinates": [[2.18], [2.16, 41.41]]},
        {"type": "Point", "coordinates": [2.18, 41.4]},
        {"coordinates": [[2.18, 41.4], [2.16, 41.41]]},
    ],
)
def test_geometry_rejects_inconsistent_nesting_and_unknown_tags(payload):
    with pytest.raises(ValidationError):
        TypeAdapter(Geometry).validate_python(payload)


def test_nested_multiline_geometry_and_projected_crs_are_retained(respond, lines_payload):
    lines_payload["crs"] = {"type": "name", "properties": {"name": "EPSG:25831"}}
    lines_payload["features"][0]["geometry"] = {
        "type": "MultiLineString",
        "coordinates": [[[430000.5, 4580000.25], [430010.5, 4580020.25]]],
    }
    respond(lines_payload)

    with TransitClient("dummy-id", "dummy-key") as client:
        response = client.fetch_lines("bus", srs_name=25831)

    assert isinstance(response.features[0].geometry, MultiLineString)
    assert response.features[0].geometry.coordinates == [[(430000.5, 4580000.25), (430010.5, 4580020.25)]]
    assert response.crs is not None
    assert response.crs.properties.name == "EPSG:25831"


def test_invalid_nested_geometry_uses_the_library_response_error(respond, http_get, lines_payload):
    lines_payload["features"][0]["geometry"]["coordinates"] = [[[2.18, 41.4], [2.16, 41.41]]]
    response = respond(lines_payload)

    with TransitClient("dummy-id", "dummy-key") as client:
        with pytest.raises(ResponseValidationError) as caught:
            client.fetch_lines("bus")

    error = caught.value
    assert error.status_code == 200
    assert error.endpoint == "transit/linies/bus"
    location = error.validation_errors[0]["loc"]
    assert isinstance(location, tuple)
    assert location[:3] == ("features", 0, "geometry")
    assert "input" not in error.validation_errors[0]
    http_get.assert_called_once()
    response.close.assert_called_once()


@pytest.mark.parametrize(
    ("model", "payload", "missing_field"),
    [
        (BusEtaResponse, {"timestamp": 1000000}, "parades"),
        (MetroEtaResponse, {"timestamp": 1000000}, "linies"),
        (LinesResponse, {"type": "FeatureCollection", "totalFeatures": 0}, "features"),
        (BusRoutesResponse, {"type": "FeatureCollection", "totalFeatures": 0}, "features"),
        (BusRoutesConsolidatedResponse, {"type": "FeatureCollection", "totalFeatures": 0}, "features"),
    ],
)
def test_missing_root_collections_are_not_successful_empty_responses(model, payload, missing_field):
    with pytest.raises(ValidationError) as caught:
        model.model_validate(payload)

    assert caught.value.errors()[0]["loc"] == (missing_field,)
    assert caught.value.errors()[0]["type"] == "missing"
