from datetime import date as Date
from datetime import datetime
from datetime import time as Time
from zoneinfo import ZoneInfo

from pytmb._endpoint import EndpointClient
from pytmb._transport import Timeout
from pytmb._validation import is_finite_number, validate_coordinates
from pytmb.enums import TransitMode
from pytmb.exceptions import ResponseValidationError
from pytmb.models.planner import PlannerResponse


_BARCELONA = ZoneInfo("Europe/Madrid")


class PlannerClient(EndpointClient):
    """Typed route plans; standalone clients default to a 15-second timeout."""

    _default_timeout: Timeout = 15

    def fetch_plan(
        self,
        from_place: tuple[float, float],
        to_place: tuple[float, float],
        *,
        mode: TransitMode | list[TransitMode] | None = None,
        date: Date | None = None,
        time: Time | None = None,
        arrive_by: bool = False,
        max_walk_distance: float | None = None,
        show_intermediate_stops: bool | None = None,
    ) -> PlannerResponse:
        """Fetch a successful typed plan without itinerary formatting or rounding.

        Args:
            from_place: Origin (latitude, longitude).
            to_place: Destination (latitude, longitude).
            mode: One mode or a nonempty list; defaults to TRANSIT,WALK.
            date: Date, defaulting to today in Barcelona.
            time: Barcelona-local time, defaulting to now. Aware times are combined
                with `date` in their timezone and converted to Barcelona, including
                any date rollover.
            arrive_by: Interpret the requested date/time as arrival instead of departure.
            max_walk_distance: Optional finite, nonnegative distance in meters.
            show_intermediate_stops: Include intermediate stops in itinerary legs.

        Use `pytmb.summaries.summarize_plan` for an independent domain view.
        Planner application errors raise `APIError`; a missing plan raises
        `ResponseValidationError`.
        """
        validate_coordinates(from_place, "from_place")
        validate_coordinates(to_place, "to_place")
        if max_walk_distance is not None and (
            not is_finite_number(max_walk_distance) or max_walk_distance < 0
        ):
            raise ValueError("max_walk_distance must be a finite, non-negative number")

        if mode is None:
            mode_values = [TransitMode.TRANSIT.value, TransitMode.WALK.value]
        elif isinstance(mode, TransitMode):
            mode_values = [mode.value]
        elif isinstance(mode, list) and mode and all(isinstance(item, TransitMode) for item in mode):
            mode_values = [item.value for item in mode]
        else:
            raise ValueError("mode must be a TransitMode or a non-empty list of TransitMode values")

        params: dict[str, str | float] = {
            "fromPlace": f"{from_place[0]},{from_place[1]}",
            "toPlace": f"{to_place[0]},{to_place[1]}",
        }
        now = datetime.now(_BARCELONA)
        requested = datetime.combine(date if date is not None else now.date(), time if time is not None else now.timetz())
        if requested.utcoffset() is not None:
            requested = requested.astimezone(_BARCELONA)
        params["date"] = requested.strftime("%m-%d-%Y")
        period = "am" if requested.hour < 12 else "pm"
        params["time"] = f"{requested.hour % 12 or 12:02d}:{requested.minute:02d}{period}"
        params["arriveBy"] = "true" if arrive_by else "false"
        params["mode"] = ",".join(mode_values)
        if max_walk_distance is not None:
            params["maxWalkDistance"] = max_walk_distance
        if show_intermediate_stops is not None:
            params["showIntermediateStops"] = "true" if show_intermediate_stops else "false"

        response = self._get("planner/plan", PlannerResponse, params=params)
        if response.error is not None:
            raise self._transport.api_error(
                response.error.message or response.error.msg or "Planner request failed",
                endpoint="planner/plan",
                code=response.error.id,
                details=response.error.model_dump(exclude_none=True),
            )
        if response.plan is None:
            raise ResponseValidationError(
                "Planner response contains neither a plan nor an error", endpoint="planner/plan"
            )
        return response
