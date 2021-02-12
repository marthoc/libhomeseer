"""Helper functions."""

import logging
from datetime import datetime, timezone
from string import digits
from typing import Optional

HS_UNIT_CELSIUS = "C"
HS_UNIT_FAHRENHEIT = "F"
HS_UNIT_KWH = "kW Hours"
HS_UNIT_LUX = "Lux"
HS_UNIT_PERCENTAGE = "%"
HS_UNIT_WATTS = "Watts"

HS_NULL_DATE = "-62135596800000"

_LOGGER = logging.getLogger(__name__)


def get_datetime_from_last_change(last_change: str) -> Optional[datetime]:
    """Parses a last_change to return a python datetime object, or None if no datetime can be parsed."""
    if HS_NULL_DATE in last_change:
        return None

    if "-" in last_change:
        lc = last_change.split("-")[0]
    else:
        lc = last_change

    date_string = "".join(i for i in lc if i in digits)

    try:
        unix_timestamp = int(date_string) / 1000
        dt = datetime.fromtimestamp(unix_timestamp, tz=timezone.utc)
    except ValueError:
        return None

    return dt


def get_uom_from_status(status: str) -> Optional[str]:
    """Parses a status to return a unit of measure, or None if no unit can be parsed."""
    uom = None
    if HS_UNIT_CELSIUS in status:
        uom = HS_UNIT_CELSIUS
    if HS_UNIT_FAHRENHEIT in status:
        uom = HS_UNIT_FAHRENHEIT
    if HS_UNIT_KWH in status:
        uom = HS_UNIT_KWH
    if HS_UNIT_LUX in status:
        uom = HS_UNIT_LUX
    if HS_UNIT_PERCENTAGE in status:
        uom = HS_UNIT_PERCENTAGE
    if HS_UNIT_WATTS in status:
        uom = HS_UNIT_WATTS
    return uom
