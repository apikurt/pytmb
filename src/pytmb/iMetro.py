from time import time
from typing import Optional

import requests

from pytmb.models.iMetroModel import EtaResponseMetro, MetroEta


class IMetroClient:
    def __init__(self, app_id: str = None, app_key: str = None):
        if app_id is None or app_key is None:
            raise ValueError("app_id and app_key must be provided")
        self.__app_id = app_id
        self.__app_key = app_key
        self.__base_url = "https://api.tmb.cat/v1/itransit/metro/"
        self.__default_params = {"app_id": self.__app_id, "app_key": self.__app_key}

    def get_eta(
        self, station_codes: list[str], line: Optional[str] = None
    ) -> list[MetroEta]:
        """Get the estimated time of arrival (ETA) for metro trains at a specific station or stations.

        Args:
            station_codes (list[str]): The codes of the metro stations.
            line (Optional[str]): The metro line to filter by. Defaults to None and shows all lines.
        Returns:
            list[MetroEta]: List of MetroEta objects containing ETA information.
        """
        if not station_codes or len(station_codes) == 0:
            raise ValueError("At least one station code must be provided")
        endpoint = self.__base_url + "estacions"
        response = requests.get(
            endpoint,
            params={**self.__default_params, "estacions": ",".join(station_codes)},
            timeout=10,
        )
        response.raise_for_status()

        data = EtaResponseMetro.model_validate(response.json())

        # Show ETA for the specified line only if provided
        if line is not None:
            for metro_line in data.lines:
                if metro_line.line_name.lower() != line.lower():
                    metro_line.stations = []

        return [
            MetroEta(
                line_code=line.line_code,
                line_name=line.line_name,
                line_color=line.line_color,
                destination=route.destination,
                eta_minutes=((train.arrival_time - int(time() * 1000)) // 60000),
                station_code=station.station_code,
            )
            for line in data.lines
            for station in line.stations
            for route in station.line_routes
            for train in route.upcoming_trains
        ]
