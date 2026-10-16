from datetime import datetime, timezone
from email.utils import format_datetime
from traceback import format_exception
from unittest.mock import Mock, call
from urllib.parse import parse_qs, quote_plus, urlsplit

import pytest
import requests
from pydantic import BaseModel
from requests.adapters import BaseAdapter

from pytmb._transport import Transport
from pytmb.exceptions import ClientClosedError, HTTPError, ResponseValidationError, TransportError


class Payload(BaseModel):
    value: int


def response(payload=None, *, status=200, headers=None):
    result = Mock(spec=requests.Response)
    result.status_code = status
    result.headers = headers or {}
    result.json.return_value = {"value": 7} if payload is None else payload
    return result


@pytest.fixture
def pause(monkeypatch):
    wait = Mock()
    monkeypatch.setattr("pytmb._transport.sleep", wait)
    return wait


@pytest.fixture
def session():
    return Mock(spec=requests.Session)


@pytest.fixture
def transport(session):
    return Transport("dummy-id", "dummy-key", session=session)


def test_request_configuration_and_credentials_do_not_mutate_caller_params(session):
    result = response()
    session.get.return_value = result
    params = {"limit": 3, "app_id": "wrong-id", "app_key": "wrong-key"}
    transport = Transport(
        "dummy-id", "dummy-key", session=session, base_url="https://mirror.example/api/v1", timeout=(2, 8)
    )

    assert transport.get_model("/items", Payload, params=params).value == 7

    session.get.assert_called_once_with(
        "https://mirror.example/api/v1/items",
        params={"limit": 3, "app_id": "dummy-id", "app_key": "dummy-key"},
        timeout=(2, 8),
    )
    assert params == {"limit": 3, "app_id": "wrong-id", "app_key": "wrong-key"}
    result.close.assert_called_once()
    session.mount.assert_not_called()


def test_owned_session_is_created_once_and_closed_once(monkeypatch):
    session = Mock(spec=requests.Session)
    factory = Mock(return_value=session)
    monkeypatch.setattr(requests, "Session", factory)
    transport = Transport("dummy-id", "dummy-key")
    session.get.side_effect = [response(), response()]

    transport.get_model("items", Payload)
    transport.get_model("items", Payload)
    transport.close()
    transport.close()

    factory.assert_called_once_with()
    assert session.get.call_count == 2
    session.close.assert_called_once()
    assert transport.closed


def test_borrowed_session_is_not_closed_and_closed_transport_cannot_send(transport, session):
    transport.close()

    with pytest.raises(ClientClosedError) as caught:
        transport.get_model("items", Payload)

    assert caught.value.attempts == 0
    session.close.assert_not_called()
    session.get.assert_not_called()


@pytest.mark.parametrize("status", [301, 400, 401, 403, 404])
def test_nonretryable_http_errors_have_safe_context(transport, session, pause, status):
    result = response(status=status, headers={"X-Request-ID": "request-123"})
    session.get.return_value = result

    with pytest.raises(HTTPError) as caught:
        transport.get_model("items", Payload)

    error = caught.value
    assert error.endpoint == "items"
    assert error.status_code == status
    assert error.request_id == "request-123"
    assert error.attempts == 1
    session.get.assert_called_once()
    result.json.assert_not_called()
    result.close.assert_called_once()
    pause.assert_not_called()
    assert "dummy-key" not in str(error)


@pytest.mark.parametrize("status", [429, 500, 502, 503, 504])
def test_transient_http_errors_retry_and_close_before_waiting(transport, session, pause, status):
    first, last = response(status=status), response()
    session.get.side_effect = [first, last]
    pause.side_effect = lambda delay: first.close.assert_called_once()

    assert transport.get_model("items", Payload).value == 7

    assert session.get.call_count == 2
    pause.assert_called_once_with(0.5)
    last.close.assert_called_once()


def test_retry_budget_is_shared_between_status_and_connection_failures(transport, session, pause):
    session.get.side_effect = [response(status=503), requests.Timeout("dummy-key"), response()]

    assert transport.get_model("items", Payload).value == 7

    assert session.get.call_count == 3
    assert pause.call_args_list == [call(0.5), call(1.0)]


def test_exhausted_http_retries_preserve_final_status_and_retry_after(session, pause):
    transport = Transport("dummy-id", "dummy-key", session=session, max_retries=1)
    first = response(status=503)
    last = response(status=429, headers={"Retry-After": "5", "X-Correlation-ID": "correlation-1"})
    session.get.side_effect = [first, last]

    with pytest.raises(HTTPError) as caught:
        transport.get_model("items", Payload)

    assert caught.value.status_code == 429
    assert caught.value.request_id == "correlation-1"
    assert caught.value.retry_after == 5
    assert caught.value.attempts == 2
    assert session.get.call_count == 2
    last.close.assert_called_once()
    pause.assert_called_once_with(0.5)


@pytest.mark.parametrize(
    ("retry_after", "expected_delay"), [("2", 2), ("invalid", 0.5), ("nan", 0.5), ("-1", 0.5)]
)
def test_retry_after_seconds_and_invalid_headers(session, pause, retry_after, expected_delay):
    transport = Transport("dummy-id", "dummy-key", session=session, max_retry_delay=3)
    session.get.side_effect = [response(status=429, headers={"Retry-After": retry_after}), response()]

    transport.get_model("items", Payload)

    pause.assert_called_once_with(expected_delay)


def test_excessive_retry_after_is_reported_instead_of_retrying_early(session, pause):
    transport = Transport("dummy-id", "dummy-key", session=session, max_retry_delay=3)
    result = response(status=429, headers={"Retry-After": "1000"})
    session.get.return_value = result

    with pytest.raises(HTTPError) as caught:
        transport.get_model("items", Payload)

    assert caught.value.retry_after == 1000
    assert caught.value.attempts == 1
    session.get.assert_called_once()
    result.close.assert_called_once()
    pause.assert_not_called()


@pytest.mark.parametrize(("retry_at", "expected_delay"), [(1002, 2), (999, None)])
def test_retry_after_http_date(transport, session, pause, monkeypatch, retry_at, expected_delay):
    monkeypatch.setattr("pytmb._transport.time", lambda: 1000)
    header = format_datetime(datetime.fromtimestamp(retry_at, tz=timezone.utc), usegmt=True)
    session.get.side_effect = [response(status=503, headers={"Retry-After": header}), response()]

    transport.get_model("items", Payload)

    if expected_delay is None:
        pause.assert_not_called()
    else:
        pause.assert_called_once_with(expected_delay)


def test_exponential_backoff_is_bounded(session, pause):
    transport = Transport("dummy-id", "dummy-key", session=session, max_retries=3, max_retry_delay=0.75)
    session.get.side_effect = [response(status=503) for _ in range(4)]

    with pytest.raises(HTTPError) as caught:
        transport.get_model("items", Payload)

    assert caught.value.attempts == 4
    assert pause.call_args_list == [call(0.5), call(0.75), call(0.75)]


@pytest.mark.parametrize("error_type", [requests.Timeout, requests.ConnectionError])
def test_network_failures_are_bounded_and_tracebacks_omit_credentials(transport, session, pause, error_type):
    secret_url = "https://api.tmb.cat/items?app_id=dummy-id&app_key=dummy-key"
    session.get.side_effect = error_type(secret_url)

    with pytest.raises(TransportError) as caught:
        transport.get_model("items", Payload)

    error = caught.value
    assert error.attempts == 3
    assert error.reason == ("timeout" if error_type is requests.Timeout else "connection")
    assert session.get.call_count == 3
    assert pause.call_count == 2
    rendered = "".join(format_exception(type(error), error, error.__traceback__))
    assert "dummy-key" not in rendered
    assert "dummy-id" not in rendered


@pytest.mark.parametrize("error_type", [requests.exceptions.SSLError, requests.exceptions.InvalidURL])
def test_configuration_and_tls_failures_are_not_retried(transport, session, pause, error_type):
    session.get.side_effect = error_type("dummy-key")

    with pytest.raises(TransportError) as caught:
        transport.get_model("items", Payload)

    assert caught.value.attempts == 1
    session.get.assert_called_once()
    pause.assert_not_called()


def test_retries_can_be_disabled(session, pause):
    transport = Transport("dummy-id", "dummy-key", session=session, max_retries=0)
    session.get.return_value = response(status=503)

    with pytest.raises(HTTPError) as caught:
        transport.get_model("items", Payload)

    assert caught.value.attempts == 1
    session.get.assert_called_once()
    pause.assert_not_called()


def test_invalid_json_is_not_retried_or_exposed(transport, session, pause):
    result = response()
    result.json.side_effect = ValueError("Invalid document containing dummy-key")
    session.get.return_value = result

    with pytest.raises(ResponseValidationError, match="invalid JSON") as caught:
        transport.get_model("items", Payload)

    assert caught.value.status_code == 200
    assert caught.value.validation_errors == []
    assert "dummy-key" not in "".join(format_exception(caught.type, caught.value, caught.tb))
    result.close.assert_called_once()
    session.get.assert_called_once()
    pause.assert_not_called()


def test_model_errors_preserve_locations_without_raw_inputs(transport, session, pause):
    result = response({"value": "dummy-key"}, headers={"X-Request-ID": "request-dummy-id"})
    session.get.return_value = result

    with pytest.raises(ResponseValidationError) as caught:
        transport.get_model("items", Payload)

    error = caught.value
    assert error.validation_errors[0]["loc"] == ("value",)
    assert error.validation_errors[0]["type"] == "int_parsing"
    assert "input" not in error.validation_errors[0]
    assert "ctx" not in error.validation_errors[0]
    assert error.request_id == "request-[REDACTED]"
    assert "dummy-key" not in repr(vars(error))
    assert "dummy-key" not in "".join(format_exception(caught.type, error, caught.tb))
    result.close.assert_called_once()
    pause.assert_not_called()


def test_model_error_locations_redact_upstream_dictionary_keys(transport, session):
    class DictionaryPayload(BaseModel):
        values: dict[str, int]

    session.get.return_value = response({"values": {"dummy-key": "not an integer"}})

    with pytest.raises(ResponseValidationError) as caught:
        transport.get_model("items", DictionaryPayload)

    assert caught.value.validation_errors[0]["loc"] == ("values", "[REDACTED]")
    assert "dummy-key" not in repr(caught.value.validation_errors)


def test_application_error_metadata_is_recursively_redacted(session):
    secret = "secret+/ &=?"
    transport = Transport("dummy-id", secret, session=session)
    error = transport.api_error(
        f"Rejected {secret} and {quote_plus(secret)}",
        endpoint="planner/plan",
        code=400,
        details={"app_key": "unknown-key", "nested": [{"message": f"dummy-id:{secret}"}]},
    )

    assert error.code == 400
    assert error.endpoint == "planner/plan"
    assert error.details["app_key"] == "[REDACTED]"
    assert secret not in str(error)
    assert quote_plus(secret) not in str(error)
    assert "dummy-id" not in repr(error.details)
    assert secret not in repr(error.details)


@pytest.mark.parametrize(
    "settings",
    [
        {"app_id": ""},
        {"app_key": " "},
        {"base_url": "api.tmb.cat/v1"},
        {"base_url": "https://user:password@example.com/v1"},
        {"base_url": "https://example.com/v1?app_key=secret"},
        {"base_url": "https://example.com/v1#fragment"},
        {"base_url": "https://[invalid"},
        {"timeout": 0},
        {"timeout": True},
        {"timeout": (1, -1)},
        {"timeout": (1,)},
        {"timeout": float("inf")},
        {"max_retries": -1},
        {"max_retries": True},
        {"max_retries": 1.5},
        {"backoff_factor": -1},
        {"max_retry_delay": float("nan")},
    ],
)
def test_invalid_configuration_fails_before_creating_a_session(monkeypatch, settings):
    factory = Mock()
    monkeypatch.setattr(requests, "Session", factory)
    kwargs = {"app_id": "dummy-id", "app_key": "dummy-key", **settings}

    with pytest.raises(ValueError):
        Transport(**kwargs)

    factory.assert_not_called()


@pytest.mark.parametrize("path", ["https://other.example/items", "//other.example/items", "../items", "items?x=1"])
def test_endpoint_cannot_override_the_configured_api_root(transport, session, path):
    with pytest.raises(ValueError, match="relative path"):
        transport.get_model(path, Payload)

    session.get.assert_not_called()


def test_real_session_uses_the_same_adapter_for_repeated_prepared_requests():
    class RecordingAdapter(BaseAdapter):
        def __init__(self):
            self.requests = []
            self.timeouts = []
            self.close_count = 0

        def send(self, request, stream=False, timeout=None, verify=True, cert=None, proxies=None):
            self.requests.append(request)
            self.timeouts.append(timeout)
            result = requests.Response()
            result.status_code = 200
            result._content = b'{"value": 7}'
            return result

        def close(self):
            self.close_count += 1

    adapter = RecordingAdapter()
    with requests.Session() as session:
        session.mount("https://", adapter)
        transport = Transport("dummy-id", "dummy-key", session=session, timeout=(2, 4))

        transport.get_model("items", Payload)
        transport.get_model("items", Payload)
        transport.close()

        assert adapter.close_count == 0
        assert len(adapter.requests) == 2
        assert adapter.timeouts == [(2, 4), (2, 4)]
        assert parse_qs(urlsplit(adapter.requests[0].url).query) == {"app_id": ["dummy-id"], "app_key": ["dummy-key"]}

    assert adapter.close_count == 1
