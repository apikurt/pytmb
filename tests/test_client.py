from datetime import date, time
from unittest.mock import Mock

import pytest
import requests

from pytmb import (
    APIError,
    ClientClosedError,
    HTTPError,
    BusClient,
    MetroClient,
    PlannerClient,
    ResponseValidationError,
    TMBClient,
    TransitClient,
)


ENDPOINTS = [
    (BusClient, "fetch_eta", ("1234",), "itransit/bus/parades/1234"),
    (MetroClient, "fetch_eta", ([123],), "itransit/metro/estacions"),
    (PlannerClient, "fetch_plan", ((41.4, 2.18), (41.41, 2.16)), "planner/plan"),
    (TransitClient, "fetch_lines", ("bus",), "transit/linies/bus"),
    (TransitClient, "fetch_bus_routes", (23,), "transit/linies/bus/23/recs"),
    (TransitClient, "fetch_consolidated_bus_routes", (23,), "transit/linies/bus/23/recs/cons"),
]


@pytest.fixture
def session():
    return Mock(spec=requests.Session)


@pytest.fixture
def transit_payload():
    return {"type": "FeatureCollection", "totalFeatures": 0, "features": []}


def test_facade_shares_one_owned_session_and_request_policy(
    monkeypatch, session, make_response, bus_payload, metro_payload, planner_payload
):
    factory = Mock(return_value=session)
    monkeypatch.setattr(requests, "Session", factory)
    empty_features = {"type": "FeatureCollection", "totalFeatures": 0, "features": []}
    responses = [
        make_response(payload)
        for payload in [bus_payload, metro_payload, planner_payload, empty_features, empty_features, empty_features]
    ]
    session.get.side_effect = responses

    with TMBClient("dummy-id", "dummy-key", base_url="https://mirror.example/api/v1", timeout=(2, 8)) as client:
        assert client.bus.fetch_eta("1234").stops[0].stop_code == "1234"
        assert client.metro.fetch_eta([123, 456]).lines[0].line_name == "L1"
        plan = client.planner.fetch_plan((41.4, 2.18), (41.41, 2.16), date=date(2026, 1, 1), time=time(12))
        assert plan.plan is not None
        assert len(plan.plan.itineraries) == 1
        assert client.transit.fetch_lines("metro", srs_name=4326).features == []
        assert client.transit.fetch_bus_routes(23, srs_name="25831").features == []
        assert client.transit.fetch_consolidated_bus_routes(23, srs_name="EPSG:4326").features == []
        assert not any(group.closed for group in (client.bus, client.metro, client.planner, client.transit))

    expected_paths = [
        "itransit/bus/parades/1234",
        "itransit/metro/estacions",
        "planner/plan",
        "transit/linies/metro",
        "transit/linies/bus/23/recs",
        "transit/linies/bus/23/recs/cons",
    ]
    calls = session.get.call_args_list
    assert [item.args[0] for item in calls] == [f"https://mirror.example/api/v1/{path}" for path in expected_paths]
    assert all(item.kwargs["timeout"] == (2, 8) for item in calls)
    assert all(item.kwargs["params"]["app_id"] == "dummy-id" for item in calls)
    assert all(item.kwargs["params"]["app_key"] == "dummy-key" for item in calls)
    assert calls[1].kwargs["params"]["estacions"] == "123,456"
    assert calls[2].kwargs["params"]["date"] == "01-01-2026"
    assert calls[2].kwargs["params"]["time"] == "12:00pm"
    assert [item.kwargs["params"]["srsName"] for item in calls[3:]] == ["EPSG:4326", "EPSG:25831", "EPSG:4326"]
    factory.assert_called_once_with()
    client.close()
    session.close.assert_called_once()
    assert client.closed
    assert all(group.closed for group in (client.bus, client.metro, client.planner, client.transit))
    for result in responses:
        result.close.assert_called_once()


@pytest.mark.parametrize(
    ("client_type", "method", "args", "payload_name", "timeout"),
    [
        (BusClient, "fetch_eta", ("1234",), "bus_payload", 10),
        (MetroClient, "fetch_eta", ([123],), "metro_payload", 10),
        (PlannerClient, "fetch_plan", ((41.4, 2.18), (41.41, 2.16)), "planner_payload", 15),
        (TransitClient, "fetch_lines", ("bus",), "transit_payload", 10),
    ],
)
def test_standalone_clients_accept_borrowed_sessions_and_preserve_default_timeouts(
    request, session, make_response, client_type, method, args, payload_name, timeout
):
    session.get.return_value = make_response(request.getfixturevalue(payload_name))

    with client_type("dummy-id", "dummy-key", session=session) as client:
        getattr(client, method)(*args)

    assert client.closed
    assert session.get.call_args.kwargs["timeout"] == timeout
    session.close.assert_not_called()
    session.mount.assert_not_called()
    with pytest.raises(ClientClosedError):
        client.__enter__()


def test_closing_one_group_leaves_other_groups_and_borrowed_session_usable(session, make_response, metro_payload):
    session.get.return_value = make_response(metro_payload)
    with TMBClient("dummy-id", "dummy-key", session=session) as client:
        client.bus.close()

        with pytest.raises(ClientClosedError):
            client.bus.fetch_eta("1234")
        assert not client.closed
        assert not client.metro.closed
        assert client.metro.fetch_eta([123]).lines[0].line_name == "L1"

    session.close.assert_not_called()
    session.get.assert_called_once()


def test_closing_facade_invalidates_previously_obtained_groups(session):
    client = TMBClient("dummy-id", "dummy-key", session=session)
    groups = [client.bus, client.metro, client.planner, client.transit]
    client.close()

    for group in groups:
        assert group.closed
        with pytest.raises(ClientClosedError):
            group.__enter__()
    with pytest.raises(ClientClosedError):
        client.bus.fetch_eta("1234")
    with pytest.raises(ClientClosedError):
        client.__enter__()
    session.get.assert_not_called()
    session.close.assert_not_called()


def test_context_exit_closes_owned_session_without_suppressing_caller_errors(monkeypatch, session):
    monkeypatch.setattr(requests, "Session", Mock(return_value=session))
    client = TMBClient("dummy-id", "dummy-key")

    with pytest.raises(RuntimeError, match="Caller failed"):
        with client:
            raise RuntimeError("Caller failed")

    assert client.closed
    session.close.assert_called_once()


@pytest.mark.parametrize(("client_type", "method", "args", "endpoint"), ENDPOINTS)
def test_all_endpoint_methods_use_shared_http_error_handling(
    session, make_response, client_type, method, args, endpoint
):
    result = make_response({"message": "secret body dummy-key"}, status=401, headers={"X-Request-ID": "trace-123"})
    session.get.return_value = result

    with client_type("dummy-id", "dummy-key", session=session) as client:
        with pytest.raises(HTTPError) as caught:
            getattr(client, method)(*args)

    assert caught.value.endpoint == endpoint
    assert caught.value.status_code == 401
    assert caught.value.request_id == "trace-123"
    assert "dummy-key" not in str(caught.value)
    session.get.assert_called_once()
    result.json.assert_not_called()
    result.close.assert_called_once()


@pytest.mark.parametrize(("client_type", "method", "args", "endpoint"), ENDPOINTS)
def test_all_endpoint_methods_wrap_invalid_responses(session, make_response, client_type, method, args, endpoint):
    session.get.return_value = make_response({})

    with client_type("dummy-id", "dummy-key", session=session) as client:
        with pytest.raises(ResponseValidationError) as caught:
            getattr(client, method)(*args)

    assert caught.value.endpoint == endpoint
    session.get.assert_called_once()


def test_planner_application_errors_use_transport_redaction(session, make_response):
    result = make_response({"error": {"id": 400, "msg": "Rejected dummy-key", "missing": ["dummy-id"]}})
    session.get.return_value = result

    with TMBClient("dummy-id", "dummy-key", session=session) as client:
        with pytest.raises(APIError) as caught:
            client.planner.fetch_plan((41.4, 2.18), (41.41, 2.16))

    assert caught.value.code == 400
    assert caught.value.endpoint == "planner/plan"
    assert "dummy-key" not in str(caught.value)
    assert "dummy-id" not in repr(caught.value.details)
    session.get.assert_called_once()
    result.close.assert_called_once()
