# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Added
- for new features
### Changed
- for changes in existing functionality
### Deprecated
- for soon-to-be removed features
### Removed
- for now removed features
### Fixed
- for any bug fixes
### Security
- in case of vulnerabilities

## [0.0.4] - 2019-01-03
### Added
- Status heartbeat reporting on an independent thread
- Independent sleep configuration for heartbeat and worker threads
- Configuration variable HEARTBEAT_SLEEP_DURATION_SECONDS added
- Configuration variable WORK_SLEEP_DURATION_SECONDS added
- Added application requirement requests-futures
- Added unit testing requirement pytest-asyncio
### Changed
- Use of requests changed to FuturesSession of requests-futures
- Unit tests modified for async nature of heartbeat function
- Picker documentation in doc/admin.md
### Removed
- Configuration variable SLEEP_DURATION_SECONDS removed

## [0.0.3] - 2018-12-18
### Added
- Administrator documentation in doc/admin.md
- Configuration dictionary creation in config.py
- First draft of Picker component in picker.py
- Requirements: pytest-mock and requests
### Changed
- Clean task in snake script removes another directory
### Fixed
- developers@iwe e-mail in setup.py
- lots of little flake8 issues in setup.py
- hashbang in snake script
- formatting cruft in snake script

## [0.0.2] - 2018-12-12
### Added
- Changelog for the project
- Configuration for some tools to setup.cfg
- Project helper script: snake
### Changed
- Updated documentation in README.md

## 0.0.1 - 2018-12-10
### Added
- Project setup scripts

[Unreleased]: https://github.com/WIPACrepo/lta/compare/v0.0.4...HEAD
[0.0.4]: https://github.com/WIPACrepo/lta/compare/v0.0.3...v0.0.4
[0.0.3]: https://github.com/WIPACrepo/lta/compare/v0.0.2...v0.0.3
[0.0.2]: https://github.com/WIPACrepo/lta/compare/v0.0.1...v0.0.2