from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class MetroTrain(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    service_code: str = Field(alias="codi_servei")
    arrival_time: int = Field(alias="temps_arribada")  # epoch milliseconds

    def __repr__(self):
        return f"MetroTrain(service_code={self.service_code}, arrival_time={self.arrival_time})"

    def __str__(self):
        return f"Train service={self.service_code} arrival_epoch_ms={self.arrival_time}"


class MetroRoute(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    line_code: int = Field(alias="codi_linia")
    line_name: str = Field(alias="nom_linia")
    line_color: str = Field(alias="color_linia")
    route_code: str = Field(alias="codi_trajecte")
    destination: str = Field(alias="desti_trajecte")
    upcoming_trains: list[MetroTrain] = Field(default_factory=list, alias="propers_trens")

    def __repr__(self):
        return (
            f"MetroRoute(line_code={self.line_code}, line_name={self.line_name}, "
            f"line_color={self.line_color}, route_code={self.route_code}, "
            f"destination={self.destination}, upcoming_trains={self.upcoming_trains})"
        )

    def __str__(self):
        return (
            f"Route {self.line_code} {self.line_name} dest={self.destination} trains={len(self.upcoming_trains)}"
        )


class MetroStation(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    track: int = Field(alias="codi_via")  # 1 or 2
    direction_id: int = Field(alias="id_sentit")  # 1 = outbound, 2 = return
    station_code: int = Field(alias="codi_estacio")
    line_routes: list[MetroRoute] = Field(default_factory=list, alias="linies_trajectes")

    def __repr__(self):
        return (
            f"MetroStation(track={self.track}, direction_id={self.direction_id}, "
            f"station_code={self.station_code}, line_routes={self.line_routes})"
        )

    def __str__(self):
        return (
            f"Station {self.station_code} track={self.track} dir={self.direction_id} routes={len(self.line_routes)}"
        )


class MetroLine(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    line_code: int = Field(alias="codi_linia")
    line_name: str = Field(alias="nom_linia")
    family_name: str = Field(alias="nom_familia")
    family_code: int = Field(alias="codi_familia")
    line_color: str = Field(alias="color_linia")
    stations: list[MetroStation] = Field(default_factory=list, alias="estacions")

    def __repr__(self):
        return (
            f"MetroLine(line_code={self.line_code}, line_name={self.line_name}, "
            f"family_name={self.family_name}, family_code={self.family_code}, "
            f"line_color={self.line_color}, stations={self.stations})"
        )

    def __str__(self):
        return (
            f"Line {self.line_code} {self.line_name} stations={len(self.stations)} color={self.line_color}"
        )


class MetroEtaResponse(BaseModel):
    """Response model for the Metro ETA API."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    timestamp: int  # epoch milliseconds of the query
    lines: list[MetroLine] = Field(default_factory=list, alias="linies")

    def __repr__(self):
        return f"MetroEtaResponse(timestamp={self.timestamp}, lines={self.lines})"

    def __str__(self):
        return f"MetroEtaResponse timestamp={self.timestamp} lines={len(self.lines)}"


# other models for the iMetroClient methods
class MetroEtaInfo(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    line_code: int
    line_name: str
    line_color: str  # hexadecimal color code
    destination: str
    eta_minutes: int
    station_code: int

    def __repr__(self):
        return (
            f"MetroEtaInfo(line_code={self.line_code}, line_name={self.line_name}, "
            f"line_color={self.line_color}, destination={self.destination}, eta_minutes={self.eta_minutes}, station_code={self.station_code})"
        )

    def __str__(self):
        return (
            f"Metro {self.line_name} ({self.line_code}) to {self.destination}: {self.eta_minutes} min station={self.station_code}"
        )
