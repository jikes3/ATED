from __future__ import annotations

import os
from typing import Any

import httpx

SUPERVISOR_URL = "http://supervisor"
CORE_API_URL = f"{SUPERVISOR_URL}/core/api"


def token_available() -> bool:
    return bool(os.environ.get("SUPERVISOR_TOKEN"))


def auth_headers() -> dict[str, str]:
    token = os.environ.get("SUPERVISOR_TOKEN", "")
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


async def get_json(url: str) -> Any:
    if not token_available():
        raise RuntimeError("Proměnná SUPERVISOR_TOKEN není dostupná.")
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(url, headers=auth_headers())
        response.raise_for_status()
        return response.json()


async def ha_get(path: str) -> Any:
    return await get_json(f"{CORE_API_URL}{path}")


async def supervisor_get(path: str) -> Any:
    return await get_json(f"{SUPERVISOR_URL}{path}")


async def all_states() -> list[dict[str, Any]]:
    states = await ha_get("/states")
    if not isinstance(states, list):
        raise RuntimeError("Home Assistant API nevrátilo seznam entit.")
    return [item for item in states if isinstance(item, dict)]
