"""Config flow for ATED Core."""
from __future__ import annotations

from typing import Any
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_ENTITY_IDS,
    CONF_EXPLANATION_DETAIL,
    CONF_SNAPSHOT_INTERVAL,
    DEFAULT_ENTITY_IDS,
    DEFAULT_EXPLANATION_DETAIL,
    DEFAULT_SNAPSHOT_INTERVAL,
    DOMAIN,
)


def _schema(default_entities: list[str], default_interval: int, default_detail: int) -> vol.Schema:
    return vol.Schema({
        vol.Required(CONF_ENTITY_IDS, default=default_entities): selector.EntitySelector(
            selector.EntitySelectorConfig(multiple=True)
        ),
        vol.Required(CONF_SNAPSHOT_INTERVAL, default=default_interval): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=60, max=3600, step=60,
                mode=selector.NumberSelectorMode.BOX,
                unit_of_measurement="s",
            )
        ),
        vol.Required(CONF_EXPLANATION_DETAIL, default=str(default_detail)): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[
                    selector.SelectOptionDict(value="0", label="0 – Pouze výsledek"),
                    selector.SelectOptionDict(value="1", label="1 – Stručné vysvětlení"),
                    selector.SelectOptionDict(value="2", label="2 – Pokročilé údaje"),
                    selector.SelectOptionDict(value="3", label="3 – Expert"),
                    selector.SelectOptionDict(value="4", label="4 – Vývojář"),
                ],
                mode=selector.SelectSelectorMode.DROPDOWN,
            )
        ),
    })


class AtedCoreConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> config_entries.ConfigFlowResult:
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        if user_input is not None:
            user_input[CONF_EXPLANATION_DETAIL] = int(user_input[CONF_EXPLANATION_DETAIL])
            return self.async_create_entry(title="ATED Core", data=user_input)
        return self.async_show_form(
            step_id="user",
            data_schema=_schema(DEFAULT_ENTITY_IDS, DEFAULT_SNAPSHOT_INTERVAL, DEFAULT_EXPLANATION_DETAIL),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> "AtedCoreOptionsFlow":
        return AtedCoreOptionsFlow()


class AtedCoreOptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> config_entries.ConfigFlowResult:
        if user_input is not None:
            user_input[CONF_EXPLANATION_DETAIL] = int(user_input[CONF_EXPLANATION_DETAIL])
            return self.async_create_entry(title="", data=user_input)

        current_entities = self.config_entry.options.get(
            CONF_ENTITY_IDS,
            self.config_entry.data.get(CONF_ENTITY_IDS, DEFAULT_ENTITY_IDS),
        )
        current_interval = int(self.config_entry.options.get(
            CONF_SNAPSHOT_INTERVAL,
            self.config_entry.data.get(CONF_SNAPSHOT_INTERVAL, DEFAULT_SNAPSHOT_INTERVAL),
        ))
        current_detail = int(self.config_entry.options.get(
            CONF_EXPLANATION_DETAIL,
            self.config_entry.data.get(CONF_EXPLANATION_DETAIL, DEFAULT_EXPLANATION_DETAIL),
        ))
        return self.async_show_form(
            step_id="init",
            data_schema=_schema(list(current_entities), current_interval, current_detail),
        )
