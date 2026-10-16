"""Common configuration and resource lifecycle for the endpoint clients."""

from types import TracebackType
from typing import TypeVar

import requests

from pytmb._transport import DEFAULT_BASE_URL, Model, QueryParams, Timeout, Transport
from pytmb.exceptions import ClientClosedError


Client = TypeVar("Client", bound="EndpointClient")


class EndpointClient:
    """Shared transport configuration and lifecycle for endpoint groups."""

    _default_timeout: Timeout = 10

    def __init__(
        self,
        app_id: str,
        app_key: str,
        *,
        session: requests.Session | None = None,
        base_url: str = DEFAULT_BASE_URL,
        timeout: Timeout | None = None,
        max_retries: int = 2,
        backoff_factor: float = 0.5,
        max_retry_delay: float = 30,
    ) -> None:
        """Configure a standalone client.

        `session` is borrowed when supplied. Otherwise the client owns a session
        and closes it on context exit or `close()`. `base_url` is the common API
        root. `timeout` is a positive number of seconds or a (connect, read) pair;
        None uses the endpoint's default. Retry settings apply to each GET call.
        """
        self._transport = Transport(
            app_id,
            app_key,
            session=session,
            base_url=base_url,
            timeout=self._default_timeout if timeout is None else timeout,
            max_retries=max_retries,
            backoff_factor=backoff_factor,
            max_retry_delay=max_retry_delay,
        )
        self._owns_transport = True
        self._closed = False

    @classmethod
    def _from_transport(cls: type[Client], transport: Transport) -> Client:
        # Bound endpoint groups borrow an already configured transport.
        client = cls.__new__(cls)
        client._transport = transport
        client._owns_transport = False
        client._closed = False
        return client

    @property
    def closed(self) -> bool:
        return self._closed or self._transport.closed

    def _ensure_open(self) -> None:
        if self.closed:
            raise ClientClosedError("Client is closed", attempts=0)

    def _get(self, path: str, model: type[Model], *, params: QueryParams | None = None) -> Model:
        self._ensure_open()
        return self._transport.get_model(path, model, params=params)

    def close(self) -> None:
        if not self._closed:
            self._closed = True
            if self._owns_transport:
                self._transport.close()

    def __enter__(self: Client) -> Client:
        self._ensure_open()
        return self

    def __exit__(
        self, exc_type: type[BaseException] | None, exc_value: BaseException | None, traceback: TracebackType | None
    ) -> None:
        self.close()
