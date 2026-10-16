from pytmb._endpoint import EndpointClient
from pytmb.models.bus import BusEtaResponse


class BusClient(EndpointClient):
    """Bus predictions returned as complete typed responses."""

    def fetch_eta(self, stop_code: str) -> BusEtaResponse:
        """Fetch predictions without filtering, summary conversion, or clock reads.

        Use `pytmb.summaries.summarize_bus` or `filter_bus` for independent views.
        Unknown upstream fields follow the response models' documented policy.
        """
        return self._get(f"itransit/bus/parades/{stop_code}", BusEtaResponse)
