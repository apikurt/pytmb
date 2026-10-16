"""Shared synchronous HTTP transport; endpoint semantics live in the clients."""

from collections.abc import Mapping
from datetime import timezone
from email.utils import parsedate_to_datetime
from time import sleep, time
from typing import Literal, TypeVar, cast
from urllib.parse import quote, quote_plus, urlsplit

import requests
from pydantic import BaseModel, ValidationError

from pytmb._validation import is_finite_number
from pytmb.exceptions import APIError, ClientClosedError, HTTPError, ResponseValidationError, TransportError


DEFAULT_BASE_URL = "https://api.tmb.cat/v1/"
Timeout = float | tuple[float, float]
QueryParams = Mapping[str, str | int | float | bool]
Model = TypeVar("Model", bound=BaseModel)
_RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})


class Transport:
    def __init__(
        self,
        app_id: str,
        app_key: str,
        *,
        session: requests.Session | None = None,
        base_url: str = DEFAULT_BASE_URL,
        timeout: Timeout = 10,
        max_retries: int = 2,
        backoff_factor: float = 0.5,
        max_retry_delay: float = 30,
    ) -> None:
        if not all(isinstance(value, str) and value.strip() for value in (app_id, app_key)):
            raise ValueError("app_id and app_key must be non-empty strings")
        self._base_url = self._validate_base_url(base_url)
        timeouts = timeout if isinstance(timeout, tuple) else (timeout,)
        if (
            isinstance(timeout, tuple) and len(timeout) != 2
        ) or not all(is_finite_number(value) and value > 0 for value in timeouts):
            raise ValueError("timeout must be a positive number or a (connect, read) pair of positive numbers")
        if isinstance(max_retries, bool) or not isinstance(max_retries, int) or max_retries < 0:
            raise ValueError("max_retries must be a non-negative integer")
        for name, value in (("backoff_factor", backoff_factor), ("max_retry_delay", max_retry_delay)):
            if not is_finite_number(value) or value < 0:
                raise ValueError(f"{name} must be a finite, non-negative number")

        self._credentials = {"app_id": app_id, "app_key": app_key}
        self._secrets = sorted(
            {encoded for value in (app_id, app_key) for encoded in (value, quote(value, safe=""), quote_plus(value))},
            key=len,
            reverse=True,
        )
        self._timeout = timeout
        self._max_retries = max_retries
        self._backoff_factor = backoff_factor
        self._max_retry_delay = max_retry_delay
        self._owns_session = session is None
        self._session = requests.Session() if session is None else session
        self._closed = False

    @staticmethod
    def _validate_base_url(base_url: str) -> str:
        message = "base_url must be an absolute HTTP(S) URL without credentials, query, or fragment"
        if not isinstance(base_url, str) or base_url != base_url.strip():
            raise ValueError(message)
        try:
            parts = urlsplit(base_url)
        except ValueError:
            raise ValueError(message) from None
        if (
            parts.scheme not in ("http", "https")
            or not parts.netloc
            or parts.username is not None
            or parts.password is not None
            or parts.query
            or parts.fragment
        ):
            raise ValueError(message)
        return base_url.rstrip("/") + "/"

    @property
    def closed(self) -> bool:
        return self._closed

    def close(self) -> None:
        if not self._closed:
            self._closed = True
            if self._owns_session:
                self._session.close()

    def _redact_text(self, text: str) -> str:
        for secret in self._secrets:
            text = text.replace(secret, "[REDACTED]")
        return text

    def _redact(self, value: object) -> object:
        if isinstance(value, str):
            return self._redact_text(value)
        if isinstance(value, dict):
            return {
                self._redact_text(str(key)): "[REDACTED]"
                if str(key).lower() in ("app_id", "app_key")
                else self._redact(item)
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [self._redact(item) for item in value]
        if isinstance(value, tuple):
            return tuple(self._redact(item) for item in value)
        return value

    def api_error(
        self, message: str, *, endpoint: str, code: int | None = None, details: dict[str, object] | None = None
    ) -> APIError:
        return APIError(
            self._redact_text(message),
            endpoint=self._redact_text(endpoint),
            code=code,
            details=cast(dict[str, object], self._redact(details)) if details is not None else None,
        )

    @staticmethod
    def _retry_after(response: requests.Response) -> float | None:
        value = response.headers.get("Retry-After")
        if value is None:
            return None
        try:
            seconds = float(value)
        except ValueError:
            try:
                retry_at = parsedate_to_datetime(value)
                if retry_at.tzinfo is None:
                    retry_at = retry_at.replace(tzinfo=timezone.utc)
                return max(0.0, retry_at.timestamp() - time())
            except (TypeError, ValueError, OverflowError):
                return None
        return seconds if is_finite_number(seconds) and seconds >= 0 else None

    def _wait(self, backoff: float, retry_after: float | None = None) -> None:
        delay = min(backoff if retry_after is None else retry_after, self._max_retry_delay)
        if delay > 0:
            sleep(delay)

    def get_model(self, path: str, model: type[Model], *, params: QueryParams | None = None) -> Model:
        if self._closed:
            raise ClientClosedError("Client is closed", attempts=0)
        parts = urlsplit(path)
        if parts.scheme or parts.netloc or parts.query or parts.fragment or ".." in parts.path.split("/"):
            raise ValueError("Endpoint must be a relative path without a query or fragment")
        path = path.lstrip("/")
        endpoint = self._redact_text(path)
        query = dict(params) if params is not None else {}
        query.update(self._credentials)
        backoff = min(self._backoff_factor, self._max_retry_delay)

        for attempt in range(self._max_retries + 1):
            try:
                response = self._session.get(self._base_url + path, params=query, timeout=self._timeout)
            except requests.RequestException as exc:
                retryable = isinstance(exc, (requests.Timeout, requests.ConnectionError)) and not isinstance(
                    exc, requests.exceptions.SSLError
                )
                if retryable and attempt < self._max_retries:
                    self._wait(backoff)
                    backoff = min(backoff * 2, self._max_retry_delay)
                    continue
                reason: Literal["timeout", "connection", "request"] = "request"
                if isinstance(exc, requests.Timeout):
                    reason = "timeout"
                elif isinstance(exc, requests.ConnectionError):
                    reason = "connection"
                raise TransportError(
                    f"GET {endpoint} failed ({reason})",
                    endpoint=endpoint,
                    reason=reason,
                    attempts=attempt + 1,
                ) from None

            try:
                retry_after = self._retry_after(response)
                if (
                    response.status_code not in _RETRY_STATUSES
                    or attempt == self._max_retries
                    or (retry_after is not None and retry_after > self._max_retry_delay)
                ):
                    return self._decode(response, model, endpoint, attempt + 1, retry_after)
            finally:
                response.close()
            self._wait(backoff, retry_after)
            backoff = min(backoff * 2, self._max_retry_delay)

        raise AssertionError("Unreachable retry state")

    def _decode(
        self, response: requests.Response, model: type[Model], endpoint: str, attempts: int, retry_after: float | None
    ) -> Model:
        request_id = response.headers.get("X-Request-ID") or response.headers.get("X-Correlation-ID")
        if request_id is not None:
            request_id = self._redact_text(request_id)
        if not 200 <= response.status_code < 300:
            raise HTTPError(
                f"GET {endpoint} returned HTTP {response.status_code}",
                endpoint=endpoint,
                status_code=response.status_code,
                request_id=request_id,
                attempts=attempts,
                retry_after=retry_after,
            )
        try:
            data = response.json()
        except ValueError:
            raise ResponseValidationError(
                f"GET {endpoint} returned invalid JSON",
                endpoint=endpoint,
                status_code=response.status_code,
                request_id=request_id,
                attempts=attempts,
            ) from None
        try:
            return model.model_validate(data)
        except ValidationError as exc:
            errors = exc.errors(include_input=False, include_context=False, include_url=False)
            raise ResponseValidationError(
                f"GET {endpoint} returned an invalid {model.__name__} response",
                endpoint=endpoint,
                status_code=response.status_code,
                request_id=request_id,
                attempts=attempts,
                validation_errors=cast(list[dict[str, object]], self._redact(errors)),
            ) from None
