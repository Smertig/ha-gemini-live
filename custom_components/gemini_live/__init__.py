"""Live voice-model integration for Gemini and OpenAI."""

from collections.abc import Iterable, Mapping
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import llm

from . import conversation, stt, tts  # noqa: F401
from .const import (
    CONF_DETAILED_LOGGING,
    DOMAIN,
    GEMINI_SESSION_MANAGER_KEY,
    GEMINI_TURN_STORE_KEY,
    LLM_APIS_KEY,
)
from .runtime import LiveSessionManager, TurnStore
from .utils import set_detailed_logging

_LOGGER = logging.getLogger(__name__)

def async_setup_runtime(
    hass: HomeAssistant,
    entry_id: str,
    config: Mapping[str, Any],
    llm_apis: Iterable[llm.API] = (),
) -> None:
    """Create the runtime state the entities of one entry read.

    Integrations that host these entities themselves call this instead of
    setting up a config entry. ``llm_apis`` are selectable by id in
    ``CONF_LLM_HASS_API`` without being registered in Home Assistant.
    """
    if entry_id in hass.data.setdefault(DOMAIN, {}):
        raise ValueError(f"Live-model runtime {entry_id} is already set up")
    set_detailed_logging(bool(config.get(CONF_DETAILED_LOGGING, False)))
    hass.data[DOMAIN][entry_id] = {
        **config,
        GEMINI_SESSION_MANAGER_KEY: LiveSessionManager(),
        GEMINI_TURN_STORE_KEY: TurnStore(),
        LLM_APIS_KEY: {api.id: api for api in llm_apis},
    }

async def async_teardown_runtime(hass: HomeAssistant, entry_id: str) -> None:
    """Close the entry's live sessions and drop its runtime state."""
    if (entry_data := hass.data.get(DOMAIN, {}).pop(entry_id, None)) is not None:
        await entry_data[GEMINI_SESSION_MANAGER_KEY].async_close_all()

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a live voice-model provider from a config entry."""
    async_setup_runtime(hass, entry.entry_id, {**entry.data, **entry.options})

    # Register options update listener to reload integration when changed
    entry.async_on_unload(entry.add_update_listener(update_listener))

    # Forward setup to the platforms
    await hass.config_entries.async_forward_entry_setups(entry, ["stt", "tts", "conversation"])
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, ["stt", "tts", "conversation"]
    )
    if unload_ok:
        await async_teardown_runtime(hass, entry.entry_id)
    return unload_ok

async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update by reloading the entry."""
    _LOGGER.debug("Live model entry updated, reloading")
    await hass.config_entries.async_reload(entry.entry_id)
