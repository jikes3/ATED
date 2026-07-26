"""ATED Core integration."""
from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import Event, HomeAssistant
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval

from .const import (
    CONF_ENTITY_IDS,
    CONF_EXPLANATION_DETAIL,
    CONF_SNAPSHOT_INTERVAL,
    DEFAULT_ENTITY_IDS,
    DEFAULT_EXPLANATION_DETAIL,
    DEFAULT_SNAPSHOT_INTERVAL,
    EVENT_DATA_DIRECTORY,
    PLATFORMS,
)
from .device_registry import AtedDeviceRegistry
from .event_intelligence import (
    ActionCorrelator,
    ActionOrigin,
    ActionRecord,
    EventActor,
    EventContext,
    EventJournal,
    JournalEvent,
    JournalEventType,
)
from .logger import AtedHistorian
from .models import AtedRuntimeData
from .presentation import DetailLevel, PresentationEngine

type AtedConfigEntry = ConfigEntry[AtedRuntimeData]


async def async_setup_entry(hass: HomeAssistant, entry: AtedConfigEntry) -> bool:
    """Set up ATED Core from a config entry."""
    entity_ids = entry.options.get(CONF_ENTITY_IDS, entry.data.get(CONF_ENTITY_IDS, DEFAULT_ENTITY_IDS))
    snapshot_interval = int(entry.options.get(
        CONF_SNAPSHOT_INTERVAL,
        entry.data.get(CONF_SNAPSHOT_INTERVAL, DEFAULT_SNAPSHOT_INTERVAL),
    ))
    detail = int(entry.options.get(
        CONF_EXPLANATION_DETAIL,
        entry.data.get(CONF_EXPLANATION_DETAIL, DEFAULT_EXPLANATION_DETAIL),
    ))

    historian = AtedHistorian(hass, entity_ids)
    await historian.async_initialize()

    device_registry = AtedDeviceRegistry(hass, entity_ids, historian.base_path)
    await device_registry.async_initialize()

    event_journal = EventJournal(Path(hass.config.path(EVENT_DATA_DIRECTORY)))
    await event_journal.async_initialize()
    correlator = ActionCorrelator()
    presentation_engine = PresentationEngine(DetailLevel.coerce(detail))

    async def _state_changed(event: Event) -> None:
        old_state = event.data.get("old_state")
        new_state = event.data.get("new_state")
        entity_id = event.data.get("entity_id")
        if new_state is None or entity_id not in historian.entity_ids:
            return

        await historian.async_log_state(entity_id, new_state)

        old_available = old_state is not None and old_state.state not in ("unknown", "unavailable")
        new_available = new_state.state not in ("unknown", "unavailable")
        if old_available != new_available:
            await device_registry.async_refresh(force=True)

        result = correlator.correlate_state_change(
            target_id=entity_id,
            previous_state=old_state.state if old_state is not None else None,
            new_state=new_state.state,
            timestamp=new_state.last_updated,
            context_user_id=getattr(event.context, "user_id", None),
        )
        journal_event = JournalEvent(
            event_type=JournalEventType.STATE_CHANGE,
            actor=result.actor,
            action=ActionRecord(
                action="state_change",
                target_id=entity_id,
                state_before=old_state.state if old_state is not None else None,
                state_after=new_state.state,
            ),
            context=EventContext(related_entities={"entity_id": entity_id}),
            decision_id=result.decision_id,
            parent_event_id=result.parent_event_id,
            explanation_codes=("possible_rejection",) if result.is_possible_rejection else (),
        )
        await event_journal.async_append(journal_event)
        correlator.remember(journal_event)

    async def _snapshot(_now) -> None:
        await historian.async_log_snapshot()
        await device_registry.async_refresh(force=True)

    unsub_state = async_track_state_change_event(hass, historian.entity_ids, _state_changed)
    unsub_snapshot = async_track_time_interval(
        hass,
        _snapshot,
        timedelta(seconds=max(60, snapshot_interval)),
    )

    async def _home_assistant_started(_event: Event) -> None:
        await device_registry.async_refresh(force=True)

    unsub_started = None
    if not hass.is_running:
        unsub_started = hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _home_assistant_started)

    entry.runtime_data = AtedRuntimeData(
        historian=historian,
        device_registry=device_registry,
        event_journal=event_journal,
        action_correlator=correlator,
        presentation_engine=presentation_engine,
        unsub_state=unsub_state,
        unsub_snapshot=unsub_snapshot,
        unsub_started=unsub_started,
    )

    await historian.async_log_initial_states()
    startup_event = JournalEvent(
        event_type=JournalEventType.ACTION,
        actor=EventActor(
            origin=ActionOrigin.ATED,
            actor_id="ated_core",
            evidence=("integration_setup",),
        ),
        action=ActionRecord(
            action="initialize_event_intelligence",
            target_id="ated_core",
            state_after="read_only",
            reversible=False,
        ),
        explanation_codes=(
            "event_intelligence_initialized",
            f"presentation_level_{detail}",
        ),
    )
    await event_journal.async_append(startup_event)
    correlator.remember(startup_event)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: AtedConfigEntry) -> bool:
    """Unload ATED Core."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        entry.runtime_data.unsub_state()
        entry.runtime_data.unsub_snapshot()
        if entry.runtime_data.unsub_started is not None:
            entry.runtime_data.unsub_started()
    return unloaded
