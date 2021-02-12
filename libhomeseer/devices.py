"""Representations of API data for HomeSeer devices as Python objects."""

import logging
from typing import Callable, Optional, Union

from .const import (
    DEVICE_ZWAVE_BARRIER_OPERATOR,
    DEVICE_ZWAVE_BATTERY,
    DEVICE_ZWAVE_CENTRAL_SCENE,
    DEVICE_ZWAVE_DOOR_LOCK,
    DEVICE_ZWAVE_DOOR_LOCK_LOGGING,
    DEVICE_ZWAVE_ELECTRIC_METER,
    DEVICE_ZWAVE_FAN_STATE,
    DEVICE_ZWAVE_LUMINANCE,
    DEVICE_ZWAVE_OPERATING_STATE,
    DEVICE_ZWAVE_RELATIVE_HUMIDITY,
    DEVICE_ZWAVE_SENSOR_BINARY,
    DEVICE_ZWAVE_SENSOR_MULTILEVEL,
    DEVICE_ZWAVE_SWITCH,
    DEVICE_ZWAVE_SWITCH_BINARY,
    DEVICE_ZWAVE_SWITCH_MULTILEVEL,
    DEVICE_ZWAVE_TEMPERATURE,
)

BASIC_DEVICES = [
    DEVICE_ZWAVE_BATTERY,
    DEVICE_ZWAVE_CENTRAL_SCENE,
    DEVICE_ZWAVE_DOOR_LOCK_LOGGING,
    DEVICE_ZWAVE_ELECTRIC_METER,
    DEVICE_ZWAVE_FAN_STATE,
    DEVICE_ZWAVE_LUMINANCE,
    DEVICE_ZWAVE_OPERATING_STATE,
    DEVICE_ZWAVE_RELATIVE_HUMIDITY,
    DEVICE_ZWAVE_SENSOR_BINARY,
    DEVICE_ZWAVE_SENSOR_MULTILEVEL,
    DEVICE_ZWAVE_TEMPERATURE,
]
DIMMABLE_DEVICES = [DEVICE_ZWAVE_SWITCH_MULTILEVEL]
LOCKABLE_DEVICES = [DEVICE_ZWAVE_DOOR_LOCK]
SWITCHABLE_DEVICES = [
    DEVICE_ZWAVE_BARRIER_OPERATOR,
    DEVICE_ZWAVE_SWITCH,
    DEVICE_ZWAVE_SWITCH_BINARY,
]

CONTROL_USE_ON = 1
CONTROL_USE_OFF = 2
CONTROL_USE_LOCK = 18
CONTROL_USE_UNLOCK = 19
CONTROL_LABEL_LOCK = "Lock"
CONTROL_LABEL_UNLOCK = "Unlock"

_LOGGER = logging.getLogger(__name__)


class HomeSeerStatusDevice:
    """
    Representation of a HomeSeer device with no controls (i.e. status only).
    Base representation for all other HomeSeer device objects.
    """

    def __init__(self, raw_data: dict, request: Callable) -> None:
        self._raw_data = raw_data
        self._request = request
        self._update_callback = None
        self._suppress_update_callback = False

    @property
    def ref(self) -> int:
        """Return the HomeSeer device ref of the device."""
        return int(self._raw_data["ref"])

    @property
    def name(self) -> str:
        """Return the name of the device."""
        return self._raw_data["name"]

    @property
    def location(self) -> str:
        """Return the location parameter of the device."""
        return self._raw_data["location"]

    @property
    def location2(self) -> str:
        """Return the location2 parameter of the device."""
        return self._raw_data["location2"]

    @property
    def value(self) -> Union[int, float]:
        """Return the value of the device."""
        if "." in str(self._raw_data["value"]):
            return float(self._raw_data["value"])
        return int(self._raw_data["value"])

    @property
    def status(self) -> str:
        """Return the status of the device."""
        return self._raw_data["status"]

    @property
    def device_type_string(self) -> str:
        """Return the device type string of the device."""
        return self._raw_data["device_type_string"]

    @property
    def last_change(self) -> str:
        """Return the last change of the device."""
        return self._raw_data["last_change"]

    def register_update_callback(
        self, callback: Callable, suppress_on_connection: bool = False
    ) -> None:
        """
        Register an update callback for the device, called when the device is updated by update_data.
        Set suppress_on_connection to True to suppress the callback on listener connect and disconnect.
        """
        self._suppress_update_callback = suppress_on_connection
        self._update_callback = callback

    def update_data(self, new_data: dict = None, connection_flag: bool = False) -> None:
        """Retrieve and cache updated data for the device from the HomeSeer JSON API."""
        if new_data is not None:
            _LOGGER.debug(
                f"Updating data for {self.location2} {self.location} {self.name} ({self.ref})"
            )
            self._raw_data = new_data

        if connection_flag and self._suppress_update_callback:
            return

        if self._update_callback is not None:
            self._update_callback()


class HomeSeerControllableDevice(HomeSeerStatusDevice):
    """Base representation for all HomeSeer devices with controls."""

    def __init__(self, raw_data: dict, control_data: dict, request: Callable) -> None:
        super().__init__(raw_data, request)
        self._on_value = None
        self._off_value = None
        self._lock_value = None
        self._unlock_value = None
        self._get_control_values(control_data)

    def _get_control_values(self, control_data: dict) -> None:
        """Parses control data from the HomeSeer API to populate control values for the device."""
        for item in control_data:
            if item["ref"] == self.ref:
                control_pairs = item["ControlPairs"]
                for pair in control_pairs:
                    control_use = pair["ControlUse"]
                    control_label = pair["Label"]
                    if control_use == CONTROL_USE_ON:
                        self._on_value = pair["ControlValue"]
                    elif control_use == CONTROL_USE_OFF:
                        self._off_value = pair["ControlValue"]
                    elif (
                        control_use == CONTROL_USE_LOCK
                        or control_label == CONTROL_LABEL_LOCK
                    ):
                        self._lock_value = pair["ControlValue"]
                    elif (
                        control_use == CONTROL_USE_UNLOCK
                        or control_label == CONTROL_LABEL_UNLOCK
                    ):
                        self._unlock_value = pair["ControlValue"]
                break


class HomeSeerSwitchableDevice(HomeSeerControllableDevice):
    """Representation of a HomeSeer device that can be switched on and off."""

    @property
    def is_on(self) -> bool:
        """Return True if the device's current value is greater than its off value."""
        return self.value > self._off_value

    async def on(self) -> None:
        """Turn the device on."""
        params = {
            "request": "controldevicebyvalue",
            "ref": self.ref,
            "value": self._on_value,
        }

        await self._request("get", params=params)

    async def off(self) -> None:
        """Turn the device off."""
        params = {
            "request": "controldevicebyvalue",
            "ref": self.ref,
            "value": self._off_value,
        }

        await self._request("get", params=params)


class HomeSeerDimmableDevice(HomeSeerSwitchableDevice):
    """
    Representation of a HomeSeer device that can be dimmed
    (i.e. set to an intermediate level between on and off).
    """

    @property
    def dim_percent(self) -> float:
        """Returns a number from 0 to 1 representing the current dim percentage."""
        return self.value / self._on_value

    async def dim(self, percent: int) -> None:
        """Dim the device on a scale from 0 to 100."""
        if percent < 0 or percent > 100:
            raise ValueError("Percent must be an integer from 0 to 100")

        value = int(self._on_value * (percent / 100))

        params = {"request": "controldevicebyvalue", "ref": self.ref, "value": value}

        await self._request("get", params=params)


class HomeSeerLockableDevice(HomeSeerControllableDevice):
    """Representation of a HomeSeer device that can be locked and unlocked."""

    @property
    def is_locked(self) -> bool:
        """Return True if the device is locked."""
        return self.value == self._lock_value

    async def lock(self) -> None:
        """Lock the device."""
        params = {
            "request": "controldevicebyvalue",
            "ref": self.ref,
            "value": self._lock_value,
        }

        await self._request("get", params=params)

    async def unlock(self) -> None:
        """Unlock the device."""
        params = {
            "request": "controldevicebyvalue",
            "ref": self.ref,
            "value": self._unlock_value,
        }

        await self._request("get", params=params)


def get_device(
    raw_data: dict, control_data: dict, request: Callable
) -> Optional[
    Union[
        HomeSeerDimmableDevice,
        HomeSeerLockableDevice,
        HomeSeerStatusDevice,
        HomeSeerSwitchableDevice,
    ]
]:
    """Return an appropriate HomeSeer device object based on its device_type_string."""
    device_type_string = raw_data["device_type_string"]
    if device_type_string in BASIC_DEVICES:
        return HomeSeerStatusDevice(raw_data, request)
    elif device_type_string in DIMMABLE_DEVICES:
        return HomeSeerDimmableDevice(raw_data, control_data, request)
    elif device_type_string in LOCKABLE_DEVICES:
        return HomeSeerLockableDevice(raw_data, control_data, request)
    elif device_type_string in SWITCHABLE_DEVICES:
        return HomeSeerSwitchableDevice(raw_data, control_data, request)
    _LOGGER.debug(
        f"HomeSeer device type not supported by libhomeseer: {device_type_string} ({raw_data})"
    )
    return None
