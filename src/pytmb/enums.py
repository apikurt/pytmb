from enum import Enum


class TravelDirection(Enum):
    OUTBOUND = 1
    RETURN = 2


class BusTransitNamespace(Enum):
    TMB = "bus"
    AMB = "amb"


class TransitType(Enum):
    BUS = "bus"
    METRO = "metro"


class TransitMode(Enum):
    """
    Docs: https://docs.opentripplanner.org/en/v1.5.0/Configuration/#routing-modes
    """

    WALK = "WALK"
    TRANSIT = "TRANSIT"
    BICYCLE = "BICYCLE"
    BICYCLE_RENT = "BICYCLE_RENT"
    BICYCLE_PARK = "BICYCLE_PARK"
    CAR = "CAR"
    CAR_PARK = "CAR_PARK"
    TRAM = "TRAM"
    SUBWAY = "SUBWAY"
    RAIL = "RAIL"
    BUS = "BUS"
    FERRY = "FERRY"
    CABLE_CAR = "CABLE_CAR"
    GONDOLA = "GONDOLA"
    FUNICULAR = "FUNICULAR"
