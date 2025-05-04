from enum import Enum

class FetchFailureReason(Enum):
    """Enum to represent specific reasons for population fetch failures."""
    NO_DATA_FOR_CITY = -1
    FETCH_ERROR = -2
    NO_DATA_FOR_COMPOUND_CITY = -3 