from __future__ import annotations

from pydantic import Field

from pytmb.models._base import ResponseModel


class Accessibility(ResponseModel):
    ramp_status: str = Field(alias="estat_rampa")

    def __repr__(self):
        return f"Accessibility(ramp_status={self.ramp_status})"

    def __str__(self):
        return f"Accessibility: ramp={self.ramp_status}"


class BusInfo(ResponseModel):
    accessibility: Accessibility | None = Field(default=None, alias="accessibilitat")

    def __repr__(self):
        return f"BusInfo(accessibility={self.accessibility})"

    def __str__(self):
        if self.accessibility:
            return f"BusInfo: {self.accessibility}"
        return "BusInfo: accessibility=none"


class Bus(ResponseModel):
    arrival_time: int = Field(alias="temps_arribada")  # epoch milliseconds of predicted arrival
    bus_id: int | None = Field(default=None, alias="id_bus")  # omitted when unavailable
    info: BusInfo | None = Field(default=None, alias="info_bus")

    def __repr__(self):
        return f"Bus(arrival_time={self.arrival_time}, bus_id={self.bus_id}, info={self.info})"

    def __str__(self):
        return f"Bus {self.bus_id} arrival_epoch_ms={self.arrival_time} info={self.info}" if self.info else f"Bus {self.bus_id} arrival_epoch_ms={self.arrival_time}"


class BusLineRoute(ResponseModel):
    operator_id: int = Field(alias="id_operador")
    transit_namespace: str = Field(alias="transit_namespace")  # "bus" (TMB) or "amb" (other AMB operator)
    line_code: int | str = Field(alias="codi_linia")  # operator-specific; AMB codes can be alphanumeric
    line_name: str = Field(alias="nom_linia")
    direction_id: int = Field(alias="id_sentit")  # 1 = outbound, 2 = return
    route_code: str = Field(alias="codi_trajecte")
    destination: str = Field(alias="desti_trajecte")
    upcoming_buses: list[Bus] = Field(default_factory=list, alias="propers_busos")

    def __repr__(self):
        return f"BusLineRoute(operator_id={self.operator_id}, transit_namespace={self.transit_namespace}, line_code={self.line_code}, line_name={self.line_name}, direction_id={self.direction_id}, route_code={self.route_code}, destination={self.destination}, upcoming_buses={self.upcoming_buses})"

    def __str__(self):
        return (
            f"Line {self.line_code} {self.line_name} dest={self.destination} dir={self.direction_id} "
            f"buses={len(self.upcoming_buses)}"
        )


class BusStop(ResponseModel):
    stop_code: str = Field(alias="codi_parada")
    stop_name: str = Field(alias="nom_parada")
    line_routes: list[BusLineRoute] = Field(default_factory=list, alias="linies_trajectes")

    def __repr__(self):
        return f"BusStop(stop_code={self.stop_code}, stop_name={self.stop_name}, line_routes={self.line_routes})"

    def __str__(self):
        return f"Stop {self.stop_code} {self.stop_name} routes={len(self.line_routes)}"


class BusEtaResponse(ResponseModel):
    """Response model for the Bus ETA API."""

    timestamp: int  # epoch milliseconds when the query was executed
    stops: list[BusStop] = Field(alias="parades")

    def __repr__(self):
        return f"BusEtaResponse(timestamp={self.timestamp}, stops={self.stops})"

    def __str__(self):
        return f"BusEtaResponse timestamp={self.timestamp} stops={len(self.stops)}"
