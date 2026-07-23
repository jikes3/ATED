"""ATED Core integration."""
from __future__ import annotations

from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
)

from .const import (
    CONF_ENTITY_IDS,
    CONF_SNAPSHOT_INTERVAL,
    DEFAULT_ENTITY_IDS,
    DEFAULT_SNAPSHOT_INTERVAL,
    PLATFORMS,
)
from .logger import AtedHistorian
from .models import AtedRuntimeData

type AtedConfigEntry = ConfigEntry[AtedRuntimeData]


async def async_setup_entry(hass: HomeAssistant, entry: AtedConfigEntry) -> bool:
    """Set up ATED Core from a config entry."""
    entity_ids = entry.options.get(
        CONF_ENTITY_IDS,
        entry.data.get(CONF_ENTITY_IDS, DEFAULT_ENTITY_IDS),
    )
    snapshot_interval = int(
        entry.options.get(
            CONF_SNAPSHOT_INTERVAL,
            entry.data.get(CONF_SNAPSHOT_INTERVAL, DEFAULT_SNAPSHOT_INTERVAL),
        )
    )

    historian = AtedHistorian(hass, entity_ids)
    await historian.async_initialize()

    async def _state_changed(event: Event) -> None:
        new_state = event.data.get("new_state")
        entity_id = event.data.get("entity_id")
        if new_state is None or entity_id not in historian.entity_ids:
            return
        await historian.async_log_state(entity_id, new_state)

    async def _snapshot(_now) -> None:
        await historian.async_log_snapshot()

    unsub_state = async_track_state_change_event(
        hass,
        historian.entity_ids,
        _state_changed,
    )
    unsub_snapshot = async_track_time_interval(
        hass,
        _snapshot,
        timedelta(seconds=max(60, snapshot_interval)),
    )

    entry.runtime_data = AtedRuntimeData(
        historian=historian,
        unsub_state=unsub_state,
        unsub_snapshot=unsub_snapshot,
    )

    await historian.async_log_initial_states()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: AtedConfigEntry) -> bool:
    """Unload ATED Core."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        entry.runtime_data.unsub_state()
        entry.runtime_data.unsub_snapshot()
    return unloaded
