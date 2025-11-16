from datetime import date as Date
from datetime import datetime
from datetime import time as Time
from typing import Literal, Optional, Union, overload

import requests

from pytmb.enums import TransitMode
from pytmb.models.PlannerModel import PlannerRouteInfo, PlannerResponse


class PlannerClient:
    def __init__(self, app_id: str = None, app_key: str = None):
        if app_id is None or app_key is None:
            raise ValueError("app_id and app_key must be provided")
        self.__app_id = app_id
        self.__app_key = app_key
        self.__base_url = "https://api.tmb.cat/v1/planner/"
        self.__default_params = {"app_id": self.__app_id, "app_key": self.__app_key}

    @overload
    def calculate_routes(
        self,
        from_place: tuple[float, float],
        to_place: tuple[float, float],
        mode: Optional[Union[TransitMode, list[TransitMode]]] = None,
        date: Optional[Date] = None,
        time: Optional[Time] = None,
        arrive_by: bool = False,
        max_walk_distance: Optional[float] = None,
        show_intermediate_stops: Optional[bool] = None,
        detail: Literal["summary"] = "summary",
    ) -> list[PlannerRouteInfo]: ...

    @overload
    def calculate_routes(
        self,
        from_place: tuple[float, float],
        to_place: tuple[float, float],
        mode: Optional[Union[TransitMode, list[TransitMode]]] = None,
        date: Optional[Date] = None,
        time: Optional[Time] = None,
        arrive_by: bool = False,
        max_walk_distance: Optional[float] = None,
        show_intermediate_stops: Optional[bool] = None,
        detail: Literal["full"] = ...,
    ) -> PlannerResponse: ...

    def calculate_routes(
        self,
        from_place: tuple[float, float],
        to_place: tuple[float, float],
        mode: Optional[Union[TransitMode, list[TransitMode]]] = None,
        date: Optional[Date] = None,
        time: Optional[Time] = None,
        arrive_by: bool = False,
        max_walk_distance: Optional[float] = None,
        show_intermediate_stops: Optional[bool] = None,
        detail: Literal["summary", "full"] = "summary",
    ) -> Union[list[PlannerRouteInfo], PlannerResponse]:
        """Plan routes and return summaries by default, or the full response.

        Args:
            from_place: Origin (lat, lon).
            to_place: Destination (lat, lon).
            mode: Optional `TransitMode` or list; defaults to TRANSIT,WALK if omitted.
            date: Optional local date; defaults to today. Formatted as MM-DD-YYYY.
            time: Optional local time; defaults to now. Formatted as hh:mmam/pm.
            arrive_by: If True, `date`/`time` are arrival; otherwise departure.
            max_walk_distance: Optional max walking distance (meters).
            show_intermediate_stops: Whether to include intermediate stops.
            detail: "summary" (default) or "full".

        Returns:
            - When detail="summary": list of `PlannerItineraryInfo`.
            - When detail="full": `PlannerResponse`.

        Docs:
            https://developer.tmb.cat/api-docs/v1/planner#tag/Planner/operation/plan
        """
        if not (
            isinstance(from_place, tuple)
            and len(from_place) == 2
            and all(isinstance(coord, float) for coord in from_place)
        ):
            raise ValueError("from_place must be a tuple of two floats (latitude, longitude)")
        if not (
            isinstance(to_place, tuple) and len(to_place) == 2 and all(isinstance(coord, float) for coord in to_place)
        ):
            raise ValueError("to_place must be a tuple of two floats (latitude, longitude)")

        endpoint = self.__base_url + "plan"
        params = dict(self.__default_params)
        params["fromPlace"] = f"{from_place[0]},{from_place[1]}"
        params["toPlace"] = f"{to_place[0]},{to_place[1]}"
        now = datetime.now()
        date_obj = date if date is not None else now.date()
        time_obj = time if time is not None else now.time()
        params["date"] = date_obj.strftime("%m-%d-%Y")
        params["time"] = time_obj.strftime("%I:%M%p").lower()
        params["arriveBy"] = "true" if arrive_by else "false"
        if mode is None:
            mode_values = [TransitMode.TRANSIT.value, TransitMode.WALK.value]
        elif isinstance(mode, list):
            mode_values = [m.value for m in mode]
        else:
            mode_values = [mode.value]
        params["mode"] = ",".join(mode_values)
        if max_walk_distance is not None:
            params["maxWalkDistance"] = max_walk_distance
        if show_intermediate_stops is not None:
            params["showIntermediateStops"] = "true" if show_intermediate_stops else "false"

        response = requests.get(endpoint, params=params, timeout=15)
        response.raise_for_status()
        data = PlannerResponse.model_validate(response.json())

        if detail == "full":
            return data

        if data.plan is None:
            return []

        routes: list[PlannerRouteInfo] = []
        for it in data.plan.itineraries:
            parts_overview: list[str] = []
            parts_desc: list[str] = []
            for leg in it.legs:
                if leg.mode == TransitMode.WALK.value:
                    continue
                if leg.route is None:
                    continue
                parts_overview.append(leg.route)
                from_name = leg.from_.name or ""
                to_name = leg.to.name or ""
                parts_desc.append(f"{leg.route} ({from_name} - {to_name})")

            overview = ", ".join(parts_overview)
            description = ", ".join(parts_desc)

            duration_seconds = it.duration
            duration_minutes = round(duration_seconds / 60)
            walk_distance = round(it.walk_distance or 0)

            routes.append(
                PlannerRouteInfo(
                    overview=overview,
                    description=description,
                    duration_in_minutes=duration_minutes,
                    duration_in_seconds=duration_seconds,
                    transit_time=it.transit_time or 0,
                    waiting_time=it.waiting_time or 0,
                    walk_distance=walk_distance,
                    transfers=it.transfers or 0,
                )
            )

        return routes

    def get_shortest_route(
        self,
        from_place: tuple[float, float],
        to_place: tuple[float, float],
        **kwargs,
    ) -> Optional[PlannerRouteInfo]:
        """Get the shortest route between two places.

        Args:
            from_place: Origin (lat, lon).
            to_place: Destination (lat, lon).
            **kwargs: Additional arguments passed to `calculate_routes`.

        Returns:
            The shortest `PlannerItineraryInfo`, or None if no routes found.
        """
        routes = self.calculate_routes(from_place, to_place, **kwargs)
        if not routes:
            return None
        return min(routes, key=lambda itin: itin.duration_in_seconds)
