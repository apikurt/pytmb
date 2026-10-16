from pytmb._endpoint import EndpointClient
from pytmb.models.metro import MetroEtaResponse


class MetroClient(EndpointClient):
    """Metro predictions returned as complete typed responses."""

    def fetch_eta(self, station_codes: list[int]) -> MetroEtaResponse:
        """Fetch predictions; filtering and ETA conversion are independent."""
        if not station_codes:
            raise ValueError("At least one station code must be provided")
        return self._get(
            "itransit/metro/estacions",
            MetroEtaResponse,
            params={"estacions": ",".join(str(code) for code in station_codes)},
        )
