"""Environment data for special cases (cars and airplanes).

This module now contains only the data needed for car and airplane volume
calculations, since regular environments now send paired ACH/volume values
directly from the frontend.

The old ENV_VOLUMES lookup table has been removed as it's no longer needed
with the improved frontend architecture that pairs ACH and volume values.
"""

# OBSOLETE: Old ACH → volume lookup table (kept commented for reference/rollback)
# This is no longer used since frontend now sends paired ACH/volume values
# ENV_VOLUMES = {
#     "6.50": "500",  # Large university classroom
#     "4.30": "300",  # Middle or high school classroom
#     "3.98": "400",  # Restaurant
#     "2.00": "200",  # Large home family dinner (ambiguous with Small Congregational Hall)
#     "9.00": "80",  # Dentist's office
#     "5.30": "100",  # Hospital general examination room
#     "3.00": "5000",  # Airport terminal
#     "2.38": "1000",  # Hotel lobby
#     "2.60": "3000",  # Mall common area
#     "1.88": "2000",  # Supermarket
#     "2.09": "4000",  # Gym/Sports arena
#     "2.18": "1500",  # Museum/Gallery
#     "2.50": "800",  # Library (ambiguous with Medium Sanctuary)
#     "7.50": "100",  # Subway car
#     "54.00": "50",  # Bus with windows open
#     "7.80": "50",  # City bus with windows closed, regular stops
#     "1.42": "50",  # Bus with windows closed, no regular stops
#     "1.50": "70",  # Private Chapel
#     "4.50": "10000",  # Mega Sanctuary
#     "0.50": "150",  # Airplane (HEPA system off)
#     "0.40": "60",  # Master bedroom
#     "0.30": "100",  # Basement
# }

# Minimal fallback dict for backward compatibility (should rarely be used now)
ENV_VOLUMES = {}

# Car ACH values that correspond to an environment category handled specially
CAR_ACH_VALUES = {"1", "2.5", "6.5", "5", "30", "40", "74"}

# Airplane ACH values
AIRPLANE_ACH_VALUES = {"15.00", "0.50"}

# Car type → default volume (m³)
CAR_TYPE_VOLUMES = {
    "ordinary": "3",
    "suv": "4",
    "pickup": "3.5",
    "minivan": "4.5",
}

# Airplane type → volume mapping
AIRPLANE_TYPE_VOLUMES = {
    "small": "65",
    "medium": "125",
    "large": "215",
    "very_large": "388",
}
