"""One configured client for all supported TMB endpoint groups."""

import requests

from pytmb._endpoint import EndpointClient
from pytmb._transport import DEFAULT_BASE_URL, Timeout
from pytmb.bus import BusClient
from pytmb.metro import MetroClient
from pytmb.planner import PlannerClient
from pytmb.transit import TransitClient


class TMBClient(EndpointClient):
    """Bus, metro, planner, and transit clients sharing one session and HTTP policy.

    Internally created sessions are closed by `close()` or context exit. Supplied
    sessions are borrowed and remain caller-owned. Closing this facade invalidates
    all its groups; closing a single group invalidates only that group.
    """

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
        super().__init__(
            app_id,
            app_key,
            session=session,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            backoff_factor=backoff_factor,
            max_retry_delay=max_retry_delay,
        )
        self.bus = BusClient._from_transport(self._transport)
        self.metro = MetroClient._from_transport(self._transport)
        self.planner = PlannerClient._from_transport(self._transport)
        self.transit = TransitClient._from_transport(self._transport)
