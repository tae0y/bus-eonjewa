"""API helpers for HA KakaoMap Bus."""
from __future__ import annotations

import asyncio
import json
from typing import Any

import aiohttp

API_URL = "https://map.kakao.com/bus/stop.json?busstopid={}"
REQUEST_HEADERS = {"User-Agent": "Mozilla/5.0"}
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=10)


async def async_fetch_stop_data(
    session: aiohttp.ClientSession, stop_id: str
) -> dict[str, Any]:
    """Fetch and parse stop data from KakaoMap."""
    url = API_URL.format(stop_id)

    async with session.get(
        url,
        headers=REQUEST_HEADERS,
        timeout=REQUEST_TIMEOUT,
    ) as response:
        response.raise_for_status()
        return json.loads(await response.text())


def build_bus_dict(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Convert the KakaoMap payload into a dict keyed by bus name."""
    lines = data.get("lines")
    if not isinstance(lines, list):
        raise ValueError("Missing 'lines' key in API response")

    bus_dict: dict[str, dict[str, Any]] = {}
    for line in lines:
        name = line.get("name")
        if name:
            bus_dict[name] = line

    return bus_dict


def build_bus_labels(data: dict[str, Any]) -> dict[str, str]:
    """Build selectable bus labels for the config flow."""
    bus_dict = build_bus_dict(data)
    labels: dict[str, str] = {}

    for name, line in bus_dict.items():
        direction = line.get("arrival", {}).get("direction", "")
        label = name
        if direction:
            label += f" ({direction})"
        labels[name] = label

    return labels


def describe_api_error(err: Exception) -> str:
    """Return a user-actionable description for network and parsing failures."""
    if isinstance(err, aiohttp.ClientConnectorDNSError):
        return (
            "DNS lookup failed while contacting KakaoMap; "
            "check Home Assistant DNS and network settings"
        )
    if isinstance(err, asyncio.TimeoutError):
        return "Timed out while contacting KakaoMap"
    if isinstance(err, aiohttp.ClientError):
        return f"Error communicating with API: {err}"
    if isinstance(err, json.JSONDecodeError):
        return f"Error parsing JSON: {err}"
    if isinstance(err, ValueError):
        return str(err)
    return f"Unexpected error: {err}"
