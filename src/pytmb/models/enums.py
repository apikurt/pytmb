from enum import Enum

class TravelDirection(Enum):
    OUTBOUND = 1
    RETURN = 2

class BusTransitNamespace(Enum):
    TMB = "bus"
    AMB = "amb"