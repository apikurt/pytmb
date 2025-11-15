from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Accessibility(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    ramp_status: str = Field(alias="estat_rampa")

    def __repr__(self):
        return f"Accessibility(ramp_status={self.ramp_status})"

    def __str__(self):
        return self.__repr__()


class BusInfo(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    accessibility: Accessibility | None = Field(default=None, alias="accessibilitat")

    def __repr__(self):
        return f"BusInfo(accessibility={self.accessibility})"

    def __str__(self):
        return self.__repr__()


class Bus(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    arrival_time: int = Field(
        alias="temps_arribada"
    )  # epoch milliseconds of predicted arrival
    bus_id: int = Field(alias="id_bus")  # unique bus identifier
    info: BusInfo | None = Field(default=None, alias="info_bus")

    def __repr__(self):
        return f"Bus(arrival_time={self.arrival_time}, bus_id={self.bus_id}, info={self.info})"
    
    def __str__(self):
        return self.__repr__()


class LineRoute(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    operator_id: int = Field(alias="id_operador")
    transit_namespace: str = Field(
        alias="transit_namespace"
    )  # "bus" (TMB) or "amb" (other AMB operator)
    line_code: int = Field(alias="codi_linia")
    line_name: str = Field(alias="nom_linia")
    direction_id: int = Field(alias="id_sentit")  # 1 = outbound, 2 = return
    route_code: str = Field(alias="codi_trajecte")
    destination: str = Field(alias="desti_trajecte")
    upcoming_buses: list[Bus] = Field(default_factory=list, alias="propers_busos")

    def __repr__(self):
        return f"LineRoute(operator_id={self.operator_id}, transit_namespace={self.transit_namespace}, line_code={self.line_code}, line_name={self.line_name}, direction_id={self.direction_id}, route_code={self.route_code}, destination={self.destination}, upcoming_buses={self.upcoming_buses})"
    
    def __str__(self):
        return self.__repr__()


class Stop(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    stop_code: str = Field(alias="codi_parada")
    stop_name: str = Field(alias="nom_parada")
    line_routes: list[LineRoute] = Field(default_factory=list, alias="linies_trajectes")

    def __repr__(self):
        return f"Stop(stop_code={self.stop_code}, stop_name={self.stop_name}, line_routes={self.line_routes})"
    
    def __str__(self):
        return self.__repr__()


class EtaResponseBus(BaseModel):
    """Response model for the Bus ETA API."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    timestamp: int  # epoch milliseconds when the query was executed
    stops: list[Stop] = Field(default_factory=list, alias="parades")

    def __repr__(self):
        return f"EtaResponseBus(timestamp={self.timestamp}, stops={self.stops})"

    def __str__(self):
        return self.__repr__()


# other models for the iBusClient methods
class BusEta(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    line_code: int
    line_name: str
    destination: str
    eta_minutes: int
    stop_code: int
    ramp_status: str | None = None

    def __repr__(self):
        return (
            f"BusEta(line_code={self.line_code}, line_name={self.line_name}, "
            f"destination={self.destination}, eta_minutes={self.eta_minutes}, stop_code={self.stop_code}, ramp_status={self.ramp_status})"
        )

    def __str__(self):
        return self.__repr__()