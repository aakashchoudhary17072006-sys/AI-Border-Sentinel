"""
AI Border Sentinel - Step 5: Virtual Restricted Zone Module
Provides polygon geofencing, proximity measurement, transition events, and heading vectors.
"""

from zone.restricted_zone import (
    EVENT_ENTERED,
    EVENT_EXITED,
    EVENT_NONE,
    RestrictedZone,
    ZONE_FAR,
    ZONE_INSIDE,
    ZONE_NEAR,
)

__all__ = [
    "RestrictedZone",
    "ZONE_INSIDE",
    "ZONE_NEAR",
    "ZONE_FAR",
    "EVENT_ENTERED",
    "EVENT_EXITED",
    "EVENT_NONE",
]
