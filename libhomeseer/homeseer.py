"""
Models a connection to a HomeSeer software installation.
Sends commands via JSON API and listens for device changes via ASCII interface.
"""

from aiohttp import BasicAuth, ClientSession, ContentTypeError
from asyncio import TimeoutError
import logging

from .const import (
    DEFAULT_ASCII_PORT,
    DEFAULT_HTTP_PORT,
    DEFAULT_PASSWORD,
    DEFAULT_USERNAME,
)
from .devices import get_device
from .events import HomeSeerEvent
from .listener import Listener

_LOGGER = logging.getLogger(__name__)


class HomeSeer:
    """Representation of a HomeSeer software installation."""

    def __init__(
        self,
        host: str,
        websession: ClientSession,
        username: str = DEFAULT_USERNAME,
        password: str = DEFAULT_PASSWORD,
        http_port: int = DEFAULT_HTTP_PORT,
        ascii_port: int = DEFAULT_ASCII_PORT,
    ) -> None:
        self._host = host
        self._websession = websession
        self._auth = BasicAuth(username, password)
        self._http_port = http_port
        self._listener = Listener(
            self._host,
            username=username,
            password=password,
            ascii_port=ascii_port,
            async_message_callback=self._message_callback,
            async_connect_callback=self._connect_callback,
            async_disconnect_callback=self._disconnect_callback,
        )
        self._available = False
        self._devices = {}
        self._events = []

    @property
    def available(self) -> bool:
        """Return True if self._listener is connected to the ASCII connection."""
        return self._available

    @property
    def devices(self) -> dict:
        """Return a dict of initialized supported devices indexed by device_ref for the HomeSeer instance."""
        return self._devices

    @property
    def events(self) -> list:
        """Return a list of initialized events for the HomeSeer instance."""
        return self._events

    async def initialize(self) -> None:
        """"Retrieve devices and events from the HomeSeer instance."""
        await self._get_devices()
        await self._get_events()

    async def start_listener(self) -> None:
        """Start the ASCII listener to listen for device changes."""
        await self._listener.start()

    async def stop_listener(self) -> None:
        """Stop the ASCII listener."""
        await self._listener.stop()

    async def control_device_by_value(self, ref: int, value: int) -> None:
        """
        Provides an interface for controlling a device by value
        directly through the HomeSeer object.
        """
        params = {
            "request": "controldevicebyvalue",
            "ref": ref,
            "value": value,
        }
        await self._request("get", params=params)

    async def _request(self, method, params=None, json=None) -> dict:
        """Make a request to the HomeSeer JSON API."""
        url = f"http://{self._host}:{self._http_port}/JSON"

        try:
            async with self._websession.request(
                method,
                url,
                params=params,
                json=json,
                auth=self._auth,
            ) as result:
                result.raise_for_status()
                _LOGGER.debug(
                    f"HomeSeer request response from {self._host}: {await result.text()}"
                )
                return await result.json()

        except ContentTypeError:
            _LOGGER.debug(
                f"HomeSeer returned non-JSON response from {self._host}: {await result.text()}"
            )

        except TimeoutError:
            _LOGGER.error(f"Timeout while requesting HomeSeer data from {self._host}")

        except Exception as ex:
            _LOGGER.error(f"HomeSeer HTTP Request error from {self._host}: {ex}")

    async def _get_devices(self) -> None:
        """Populate supported devices from HomeSeer API."""
        _LOGGER.debug(f"Requesting HomeSeer devices from {self._host}")
        try:
            params = {"request": "getstatus"}
            result = await self._request("get", params=params)

            all_devices = result["Devices"]

            params = {"request": "getcontrol"}
            result = await self._request("get", params=params)

            control_data = result["Devices"]

            for device in all_devices:
                dev = get_device(device, control_data, self._request)
                if dev is not None:
                    self._devices[dev.ref] = dev

        except TypeError:
            _LOGGER.error(f"Error retrieving HomeSeer devices from {self._host}")

    async def _get_events(self) -> None:
        """Populate supported events from HomeSeer API."""
        _LOGGER.debug(f"Requesting HomeSeer events from {self._host}")
        try:
            params = {"request": "getevents"}
            result = await self._request("get", params=params)

            all_events = result["Events"]

            for event in all_events:
                ev = HomeSeerEvent(event, self._request)
                self._events.append(ev)

        except TypeError:
            _LOGGER.error(f"Error retrieving HomeSeer events from {self._host}")

    async def _message_callback(self, device_ref: str) -> None:
        """Called by the ASCII listener when a Device Change message is received."""
        try:
            device = self.devices[int(device_ref)]
        except KeyError:
            _LOGGER.debug(
                f"Device Change message received for unsupported or uninitialized device "
                f"from {self._host}: device ref {device_ref}"
            )
            return

        params = {"request": "getstatus", "ref": device.ref}
        _LOGGER.debug(f"Requesting updated data for device ref {device_ref}")
        try:
            result = await self._request("get", params=params)
            for raw_dev in result["Devices"]:
                if int(raw_dev["ref"]) == device.ref:
                    device.update_data(raw_dev)
        except Exception as ex:
            _LOGGER.error(
                f"Error retrieving updated data for device ref {device.ref} from {self._host}: {ex}"
            )

    async def _connect_callback(self) -> None:
        """Called by the ASCII listener after an ASCII connection is established."""
        _LOGGER.debug(
            f"Refreshing devices for {self._host} and setting availability to True"
        )
        self._available = True

        try:
            params = {"request": "getstatus"}
            result = await self._request("get", params=params)
            homeseer_devices = result["Devices"]

        except TypeError:
            _LOGGER.error(f"Error refreshing HomeSeer data from {self._host}")
            return

        for raw_device in homeseer_devices:
            try:
                device = self.devices[int(raw_device["ref"])]
                device.update_data(new_data=raw_device, connection_flag=True)
            except KeyError:
                _LOGGER.debug(
                    f"HomeSeer refresh data retrieved for unsupported or uninitialized device from {self._host}: "
                    f"device ref {raw_device['ref']} ({raw_device})"
                )

    async def _disconnect_callback(self) -> None:
        """Called by the ASCII listener after an ASCII connection is disconnected."""
        _LOGGER.debug(f"Setting availability for {self._host} to False")
        self._available = False

        for device in self.devices.values():
            device.update_data(connection_flag=True)
