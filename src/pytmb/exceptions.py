"""Exceptions exposed by the client library."""

from typing import Literal


class TMBError(Exception):
    """Base class for errors reported by PyTMB."""

    def __init__(
        self,
        message: str,
        *,
        endpoint: str | None = None,
        status_code: int | None = None,
        request_id: str | None = None,
        attempts: int | None = None,
    ) -> None:
        super().__init__(message)
        self.endpoint = endpoint
        self.status_code = status_code
        self.request_id = request_id
        self.attempts = attempts


class ClientClosedError(TMBError):
    """A request or context entry was attempted after the client was closed."""


class TransportError(TMBError):
    """A request failed before a usable HTTP response was received."""

    def __init__(
        self,
        message: str,
        *,
        endpoint: str,
        reason: Literal["timeout", "connection", "request"],
        attempts: int,
    ) -> None:
        super().__init__(message, endpoint=endpoint, attempts=attempts)
        self.reason = reason


class HTTPError(TMBError):
    """The server returned an unsuccessful HTTP status."""

    def __init__(
        self,
        message: str,
        *,
        endpoint: str,
        status_code: int,
        request_id: str | None = None,
        attempts: int = 1,
        retry_after: float | None = None,
    ) -> None:
        super().__init__(
            message, endpoint=endpoint, status_code=status_code, request_id=request_id, attempts=attempts
        )
        self.retry_after = retry_after


class APIError(TMBError):
    """An application-level error reported by the API, including on HTTP 200."""

    def __init__(
        self,
        message: str,
        *,
        code: int | None = None,
        details: dict[str, object] | None = None,
        endpoint: str | None = None,
    ) -> None:
        super().__init__(message, endpoint=endpoint)
        self.code = code
        self.details = dict(details) if details is not None else {}


class ResponseValidationError(TMBError):
    """JSON decoding, model validation, or response interpretation failed."""

    def __init__(
        self,
        message: str,
        *,
        endpoint: str | None = None,
        status_code: int | None = None,
        request_id: str | None = None,
        attempts: int | None = None,
        validation_errors: list[dict[str, object]] | None = None,
    ) -> None:
        super().__init__(
            message, endpoint=endpoint, status_code=status_code, request_id=request_id, attempts=attempts
        )
        self.validation_errors = validation_errors if validation_errors is not None else []
