# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A Home Assistant custom component (HACS integration) that polls the KakaoMap Bus API to provide real-time bus arrival sensors. No build system, no test runner — this is pure Python deployed by dropping files into HA's `custom_components/` directory.

## Development Workflow

There is no local test runner or build step. Testing requires a live Home Assistant instance with this component installed under `custom_components/kakaomap_bus/`. To iterate:

1. Copy the `custom_components/kakaomap_bus/` directory to your HA instance.
2. Restart HA (or reload the integration via Developer Tools > YAML).
3. Check `home-assistant.log` for errors from the `kakaomap_bus` logger.

For API shape validation, query the endpoint directly:
```
https://map.kakao.com/bus/stop.json?busstopid=BS97660
```

## Architecture

The integration follows the standard HA custom component pattern:

- **`__init__.py`** — Entry point. Creates `KakaoBusCoordinator`, registers it in `hass.data[DOMAIN][entry_id]`, and forwards setup to platforms. Registers an options update listener that reloads the entry on any config change.
- **`coordinator.py`** — `KakaoBusCoordinator(DataUpdateCoordinator)`. Owns the polling loop. Handles quiet hours (skips API calls, returns stale data). On transient errors, keeps the last good data for up to `DEFAULT_MAX_STALE_UPDATES` consecutive failures before raising `UpdateFailed`.
- **`api.py`** — Stateless HTTP helpers. `async_fetch_stop_data` does the GET with retry logic. `build_bus_dict` converts the `lines` array into a `{bus_name: line_object}` dict. `build_bus_labels` adds direction info for the config flow UI.
- **`sensor.py`** — `KakaoBusSensor(CoordinatorEntity, SensorEntity)`. One entity per selected bus route. State = `arrivalTime / 60` (minutes); returns `None` (unknown) when `NOVEHICLE` or `arrivalTime == 0`. Attributes include `next_bus_min`, `direction`, `stop_name`, `vehicle_type`.
- **`config_flow.py`** — Two-step setup: enter stop ID → select bus routes. `OptionsFlowHandler` also allows changing quiet hours and scan interval post-setup.
- **`const.py`** — All configuration keys and defaults. Scan interval: 30–600 s (default 90 s). Quiet hours default: 00:00–05:00.

## Key Design Decisions

- **One coordinator per stop, not per bus.** A single API call fetches all routes for a stop; multiple `KakaoBusSensor` entities share one coordinator via `CoordinatorEntity`.
- **Config vs. Options split.** Immutable data (`stop_id`, `stop_name`) lives in `entry.data`; mutable user preferences (`buses`, `quiet_start`, `quiet_end`, `scan_interval`) live in `entry.options`. Always read from `options` first, fall back to `data`.
- **HA shared session.** Uses `async_get_clientsession(hass)` — do not create a standalone `aiohttp.ClientSession`.
- **No external dependencies.** `manifest.json` has `"requirements": []`; `aiohttp` is provided by HA itself.

## API Reference

Endpoint: `GET https://map.kakao.com/bus/stop.json?busstopid={STOP_ID}`

Key fields used:
- `data.name` → stop display name
- `data.lines[].name` → bus route number (used as entity key)
- `data.lines[].arrival.arrivalTime` → seconds to next bus (0 = no vehicle)
- `data.lines[].arrival.arrivalTime2` → seconds to second bus
- `data.lines[].arrival.direction` → human-readable direction string

See [api_structure.md](api_structure.md) for the full schema.
