# Changelog

The changelog format is based on a subset of [Keep a changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

## [0.2.0] - 2022-06-02

### Security

- Updated httpx package to version 0.23.0 (#10)

### Removed

- Dropped support for python3.6 (#10)

## [0.1.2] - 2021-05-18

### Changed

- Replaced trio backend by anyio. This allows to support both asyncio and trio for asynchronous backend with
  async/await syntax

### Changed

- Changed trio backend to an anyio backend. This adds support to asyncio in addition to trio.

## [0.1.1] - 2020-11-02

### Fixed

- Package deployment via nox
- Package installation for the gevent backend

## [0.1.0] - 2020-11-02

### Added

- First version of the package.