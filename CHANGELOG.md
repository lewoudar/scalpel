# Changelog

The changelog format is based on a subset of [Keep a changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Changed

- updated version of gevent from 20.9.0 to 21.8.0
- Modified noxfile.py to support python 3.10 in tests.

## Version 0.1.2 - 2021-05-18

### Changed

- Replaced trio backend by anyio. This allows to support both asyncio and trio for asynchronous backend with
  async/await syntax.

### Changed

- Changed trio backend to an anyio backend. This adds support to asyncio in addition to trio.

## [0.1.1] - 2020-11-02

### Fixed

- Package deployment via nox
- Package installation for the gevent backend

## [0.1.0] - 2020-11-02

### Added

- First version of the package.