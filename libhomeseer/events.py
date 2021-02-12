"""Representation of API data for HomeSeer events as Python objects."""

from typing import Callable


class HomeSeerEvent:
    """Representation of a HomeSeer event."""

    def __init__(self, raw_data: dict, request: Callable) -> None:
        self._raw_data = raw_data
        self._request = request

    @property
    def group(self) -> str:
        """Return the group the event belongs to."""
        return self._raw_data["Group"]

    @property
    def name(self) -> str:
        """Return the name of the event."""
        return self._raw_data["Name"]

    async def run(self) -> None:
        """Run the event."""
        json = {"action": "runevent", "group": self.group, "name": self.name}
        await self._request("post", json=json)
