"""Representations of API data for HomeSeer devices as Python objects."""

import logging
from typing import Callable, Optional, Union

from .const import RELATIONSHIP_CHILD, RELATIONSHIP_ROOT, RELATIONSHIP_STANDALONE

CONTROL_USE_ON = 1
CONTROL_USE_OFF = 2
CONTROL_USE_DIM = 3
CONTROL_USE_LOCK = 18
CONTROL_USE_UNLOCK = 19
CONTROL_LABEL_LOCK = "Lock"
CONTROL_LABEL_UNLOCK = "Unlock"

SUPPORT_STATUS = 0
SUPPORT_ON = 1
SUPPORT_OFF = 2
SUPPORT_LOCK = 4
SUPPORT_UNLOCK = 8
SUPPORT_DIM = 16

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
    def device_type_string(self) -> Optional[str]:
        """Return the device type string of the device, or None for no type string (e.g. virtual device)."""
        if self._raw_data["device_type_string"]:
            return self._raw_data["device_type_string"]
        return None

    @property
    def last_change(self) -> str:
        """Return the last change of the device."""
        return self._raw_data["last_change"]

    @property
    def relationship(self) -> int:
        """
        Return the relationship of the device.
        2 = Root device (other devices may be part of this physical device)
        3 = Standalone (this is the only device that represents this physical device)
        4 = Child (this device is part of a group of devices that represent the physical device)
        """
        relationship = int(self._raw_data["relationship"])
        if relationship == RELATIONSHIP_ROOT:
            return RELATIONSHIP_ROOT
        elif relationship == RELATIONSHIP_CHILD:
            return RELATIONSHIP_CHILD
        elif relationship == RELATIONSHIP_STANDALONE:
            return RELATIONSHIP_STANDALONE
        return relationship

    @property
    def associated_devices(self) -> list:
        """
        A list of device reference numbers that are associated with this device.
        If the device is a Root device, the list contains the device reference numbers of the child devices.
        If the device is a Child device, the list will contain one device reference number of the root device.
        """
        return self._raw_data["associated_devices"]

    @property
    def interface_name(self) -> Optional[str]:
        """
        Return the name of the interface providing the device, or None for no interface (e.g. virtual device).
        Note: this parameter is present in the JSON API data but undocumented.
        """
        if self._raw_data["interface_name"]:
            return self._raw_data["interface_name"]
        return None

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


class HomeSeerSwitchableDevice(HomeSeerStatusDevice):
    """Representation of a HomeSeer device that has On and Off control pairs."""

    def __init__(
        self, raw_data: dict, request: Callable, on_value: int, off_value: int
    ) -> None:
        super().__init__(raw_data, request)
        self._on_value = on_value
        self._off_value = off_value

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
    """Representation of a HomeSeer device that has a Dim control pair."""

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


class HomeSeerLockableDevice(HomeSeerStatusDevice):
    """Representation of a HomeSeer device that has Lock and Unlock control pairs."""

    def __init__(
        self, raw_data: dict, request: Callable, lock_value: int, unlock_value: int
    ) -> None:
        super().__init__(raw_data, request)
        self._lock_value = lock_value
        self._unlock_value = unlock_value

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
    """
    Parses control_data to return an appropriate device object
    based on the control pairs detected for the device.
    On/Off = HomeSeerSwitchableDevice
    On/Off/Dim = HomeSeerDimmableDevice
    Lock/Unlock = HomeSeerLockableDevice
    other = HomeSeerStatusDevice
    """
    on_value = None
    off_value = None
    lock_value = None
    unlock_value = None
    control_pairs = None
    supported_features = SUPPORT_STATUS
    for item in control_data:
        if item["ref"] == raw_data["ref"]:
            control_pairs = item["ControlPairs"]
            for pair in control_pairs:
                control_use = pair["ControlUse"]
                control_label = pair["Label"]
                if control_use == CONTROL_USE_ON:
                    on_value = pair["ControlValue"]
                    supported_features |= SUPPORT_ON
                elif control_use == CONTROL_USE_OFF:
                    off_value = pair["ControlValue"]
                    supported_features |= SUPPORT_OFF
                elif (
                    control_use == CONTROL_USE_LOCK
                    or control_label == CONTROL_LABEL_LOCK
                ):
                    lock_value = pair["ControlValue"]
                    supported_features |= SUPPORT_LOCK
                elif (
                    control_use == CONTROL_USE_UNLOCK
                    or control_label == CONTROL_LABEL_UNLOCK
                ):
                    unlock_value = pair["ControlValue"]
                    supported_features |= SUPPORT_UNLOCK
                elif control_use == CONTROL_USE_DIM:
                    supported_features |= SUPPORT_DIM
            break

    if supported_features == SUPPORT_ON | SUPPORT_OFF:
        return HomeSeerSwitchableDevice(
            raw_data, request, on_value=on_value, off_value=off_value
        )

    elif supported_features == SUPPORT_ON | SUPPORT_OFF | SUPPORT_DIM:
        return HomeSeerDimmableDevice(
            raw_data, request, on_value=on_value, off_value=off_value
        )

    elif supported_features == SUPPORT_LOCK | SUPPORT_UNLOCK:
        return HomeSeerLockableDevice(
            raw_data, request, lock_value=lock_value, unlock_value=unlock_value
        )

    else:
        _LOGGER.debug(
            f"Failed to automatically detect device Control Pairs for device ref {raw_data['ref']}; "
            f"creating a status-only device. "
            f"If this device has controls, open an issue on the libhomeseer repo "
            f"with the following information to request support for this device: "
            f"RAW: ({raw_data}) "
            f"CONTROL: ({control_pairs})."
        )
        return HomeSeerStatusDevice(raw_data, request)
