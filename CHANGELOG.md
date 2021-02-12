# CHANGELOG
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2021-02-08
### Added
- First release of libhomeseer after deprecation of pyhs3.
- Doc strings for classes, properties, and methods.
- Type hinting for properties and methods.
- helpers.parse_datetime_from_last_change to parse the "last_change" property of a device
- More debug logging and more detail in existing debug logging.
- Support for Z-Wave Door Lock Logging and Z-Wave Electric Meter

### Changed
- Extensive code cleanup and refactoring from pyhs3; this library may not be backwards compatible with pyhs3!
- pyhs3 "HomeTroller" class renamed to "HomeSeer".
- ASCII device change now acts as a signal to update the device data via JSON (rather than updating the device value from the ASCII message directly); this introduces an extra API call per update, but is necessary to support certain devices that have a human-meaningless value but an important (and unmappable) status (note that status was not previously being updated when the ASCII listener signaled that a device change was received). 
- helpers.parse_uom changed from async to sync (no IO).

### Removed
- HASS_* helper constants (will now be handled in Home Assistant).

### Fixed
- Ping method task in Listener is now cancelled appropriately when connection is broken (previously due to a race condition it could stay running even when the connection was broken, potentially resulting in multiple concurrent ping tasks). 
- Much cleaner logic flow in Listener should now ensure connection is cleaned up appropriately on disconnect.