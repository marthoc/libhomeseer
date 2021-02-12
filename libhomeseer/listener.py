"""ASCII (Telnet) listener for HomeSeer."""

import asyncio
import logging

from .const import DEFAULT_ASCII_PORT, DEFAULT_USERNAME, DEFAULT_PASSWORD
from .errors import HomeSeerASCIIConnectionError

PING_TIMER = 60
RECONNECT_TIMER = 10
STATE_CONNECTED = "connected"
STATE_IDLE = "idle"
STATE_STOPPED = "stopped"

_LOGGER = logging.getLogger(__name__)


class Listener:
    def __init__(self, host, **kwargs):
        self._host = host
        self._port = kwargs.get("ascii_port", DEFAULT_ASCII_PORT)
        self._username = kwargs.get("username", DEFAULT_USERNAME)
        self._password = kwargs.get("password", DEFAULT_PASSWORD)
        self._async_message_callback = kwargs.get("async_message_callback")
        self._async_connect_callback = kwargs.get("async_connect_callback")
        self._async_disconnect_callback = kwargs.get("async_disconnect_callback")
        self._reader = None
        self._writer = None
        self._state = STATE_IDLE
        self._ping_task = None
        self._ping_flag = False

    @property
    def state(self):
        return self._state

    async def start(self):
        """Start the ASCII listener."""
        self._state = STATE_IDLE
        if await self._open_connection():
            asyncio.get_event_loop().create_task(self._listen())
            self._ping_task = asyncio.get_event_loop().create_task(self._ping())
        else:
            asyncio.get_event_loop().create_task(self._connect_handler())

    async def stop(self):
        """Stop and clean up the ASCII listener."""
        self._state = STATE_STOPPED
        await self._disconnect_handler()

    async def _open_connection(self) -> bool:
        """Connect and login to HomeSeer ASCII at host:port."""
        # Attempt to connect to the ASCII connection at host:port
        try:
            connection = await asyncio.open_connection(self._host, self._port)
        except OSError as ex:
            _LOGGER.error(
                f"Error opening connection to HomeSeer ASCII at {self._host}:{self._port}: {ex}"
            )
            return False
        self._reader = connection[0]
        self._writer = connection[1]
        _LOGGER.info(
            f"Successful connection to HomeSeer ASCII at {self._host}:{self._port}"
        )

        # Create auth message and write it to the ASCII connection
        auth = "au,{},{}\r\n".format(self._username, self._password).encode()
        _LOGGER.debug(
            f"Logging in to HomeSeer ASCII connection at {self._host}:{self._port}"
        )
        self._writer.write(auth)
        await self._writer.drain()

        # Read response to auth message from the ASCII connection; expecting "ok"
        msg = await self._reader.readline()
        if msg.decode().strip() == "ok":
            _LOGGER.debug(
                f"Successful login to HomeSeer ASCII at {self._host}:{self._port}"
            )
        else:
            _LOGGER.error(
                f"Failed to login to HomeSeer ASCII at {self._host}:{self._port}: {msg.decode().strip()}"
            )
            return False

        # We are connected and logged in, set the ping flag and set state to connected
        self._ping_flag = True
        self._state = STATE_CONNECTED

        # If a connect callback has been provided, call it
        if self._async_connect_callback is not None:
            await self._async_connect_callback()

        return True

    async def _listen(self):
        """Listen for ASCII messages."""
        try:
            while True:
                msg = await self._reader.readline()
                _LOGGER.debug(
                    f"ASCII message received from {self._host}:{self._port}: {msg}"
                )
                if msg == b"":
                    raise HomeSeerASCIIConnectionError
                else:
                    await self._handle_message(msg.decode())

        except HomeSeerASCIIConnectionError:
            _LOGGER.warning(f"ASCII connection to {self._host}:{self._port} closed")
            await self._disconnect_handler()

        except Exception as ex:
            _LOGGER.error(
                f"ASCII listener error from connection to {self._host}:{self._port}: {ex}"
            )
            await self._disconnect_handler()

    async def _handle_message(self, raw):
        """Handle received messages from the ASCII connection."""
        # Raw msg format is Type,Data; break the msg into its separate parts
        msg = raw.split(",")
        # Telnet connection is active so set the ping flag to reset the ping timer
        self._ping_flag = True
        # We only care about DC messages
        if msg[0] == "DC":
            # "DC" is a "Device Change" message with format "DC,ref,newval,oldval"
            if self._async_message_callback is not None:
                # Call the callback with (ref) to signal that the device has changed
                await self._async_message_callback(msg[1])
        else:
            _LOGGER.debug(
                f"Unhandled ASCII message type received from {self._host}:{self._port}: {msg[0].strip()}"
            )

    async def _ping(self):
        """Pings the ASCII connection to maintain connection."""
        try:
            while True:
                if self._ping_flag:
                    _LOGGER.debug(
                        f"Resetting ASCII ping timer for {self._host}:{self._port} to {PING_TIMER} seconds"
                    )
                    self._ping_flag = False
                else:
                    _LOGGER.debug(
                        f"Pinging ASCII connection at {self._host}:{self._port}"
                    )
                    self._writer.write("vr\r\n".encode())
                    await self._writer.drain()
                await asyncio.sleep(PING_TIMER)
        except asyncio.CancelledError:
            _LOGGER.debug(
                f"Cancelling ping task for ASCII connection at {self._host}:{self._host}"
            )
            raise

    async def _connect_handler(self):
        """Called to attempt connect/reconnect after a delay."""
        if self.state != STATE_STOPPED:
            _LOGGER.info(
                f"Attempting to connect ASCII listener to {self._host}:{self._port} in {RECONNECT_TIMER} seconds"
            )
            await asyncio.sleep(RECONNECT_TIMER)
            await self.start()

    async def _disconnect_handler(self):
        """Called after a disconnection or error from the ASCII listener."""
        if self._ping_task is not None:
            self._ping_task.cancel()

        _LOGGER.debug(f"Closing ASCII listener at {self._host}:{self._port}")
        if self._writer is not None:
            self._writer.close()

        if self._async_disconnect_callback is not None:
            await self._async_disconnect_callback()

        await self._connect_handler()
