# CHANGELOG
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.2] - 2021-02-18
### Added
- New parameter "interface_name" for HomeSeerStatusDevice; can return None if the string is empty.

### Changed
- The property "device_type_string" will now return None if the string is empty.

## [1.2.1] - 2021-02-18
### Added
- New constants RELATIONSHIP_CHILD, RELATIONSHIP_ROOT, and RELATIONSHIP_STANDALONE added to .const (and returned from the relationship property of HomeSeerStatusDevice).

## [1.2.0] - 2021-02-16
### Changed
- The get_devices method in .devices has been refactored (along with the device classes) to provide "support" for all HomeSeer devices, regardless of device_type_string. The get_devices method no longer returns device objects based on device_type_string, but instead based on the Control Pairs detected for the device. This change makes libhomeseer completely agnostic as to the technology or plug-in that provides the device. All HomeSeer devices are now supported and libhomeseer will return at least a status-only object for every device. Devices with Control Pairs that fall into certain categories (initially On/Off, On/Off/Dim, and Lock/Unlock) will have an object returned with appropriate methods (e.g. on(), off(), dim(), lock(), unlock()) that match the device's detected Control Pairs.
- The release.sh script now builds a wheel for the library in addition to the source distribution.

## [1.1.0] - 2021-02-15
### Added
- New units Amperes, kW, Volts, and Watts to the get_uom_from_status helper function.

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