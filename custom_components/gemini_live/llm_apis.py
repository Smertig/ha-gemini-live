"""Resolve the Home Assistant LLM APIs that supply the live model's tools."""

from collections.abc import Mapping
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import llm

from .const import LLM_APIS_KEY


async def async_get_llm_api(
    hass: HomeAssistant,
    entry_data: Mapping[str, Any],
    api_ids: str | list[str],
    llm_context: llm.LLMContext,
) -> llm.APIInstance:
    """Like ``llm.async_get_api``, but also finds the entry's own APIs.

    An integration hosting these entities passes its APIs to
    ``async_setup_runtime``, so they need not be registered for every agent.
    """
    own_apis: Mapping[str, llm.API] = entry_data.get(LLM_APIS_KEY, {})
    api_ids = [api_ids] if isinstance(api_ids, str) else api_ids
    if not own_apis.keys() & set(api_ids):
        return await llm.async_get_api(
            hass=hass, api_id=api_ids, llm_context=llm_context
        )
    registered = {api.id: api for api in llm.async_get_apis(hass)}
    apis: list[llm.API] = []
    for api_id in api_ids:
        if (api := own_apis.get(api_id) or registered.get(api_id)) is None:
            raise HomeAssistantError(f"API {api_id} not found")
        apis.append(api)
    api = apis[0] if len(apis) == 1 else llm.MergedAPI(apis)
    return await api.async_get_api_instance(llm_context)
