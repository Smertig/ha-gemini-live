"""Tests for LLM APIs supplied by an integration hosting the entities."""

import asyncio

from homeassistant.helpers import llm
import pytest

from custom_components.gemini_live import async_setup_runtime, async_teardown_runtime
from custom_components.gemini_live.const import DOMAIN, GEMINI_SESSION_MANAGER_KEY
from custom_components.gemini_live.llm_apis import async_get_llm_api

LLM_CONTEXT = llm.LLMContext(
    platform="test",
    context=None,
    language="en",
    assistant="conversation",
    device_id=None,
)


class PromptApi(llm.API):
    """An API whose instance carries only a prompt."""

    async def async_get_api_instance(
        self, llm_context: llm.LLMContext
    ) -> llm.APIInstance:
        return llm.APIInstance(self, f"{self.id} prompt", llm_context, [])


class FakeHass:
    """Hashable, unlike SimpleNamespace: the LLM API registry is keyed by hass."""

    def __init__(self) -> None:
        self.data: dict = {}


async def test_own_api_is_used_without_registration(monkeypatch) -> None:
    hass = FakeHass()
    async_setup_runtime(
        hass, "entry", {}, [PromptApi(hass=hass, id="own", name="Own")]
    )

    async def unexpected(**_kwargs):
        raise AssertionError("own APIs must not go through the registry")

    monkeypatch.setattr(llm, "async_get_api", unexpected)
    instance = await async_get_llm_api(
        hass, hass.data[DOMAIN]["entry"], ["own"], LLM_CONTEXT
    )

    assert instance.api_prompt == "own prompt"
    assert llm.async_get_apis(hass) == []


async def test_own_api_merges_with_registered_ones() -> None:
    hass = FakeHass()
    llm.async_register_api(hass, PromptApi(hass=hass, id="assist", name="Assist"))
    async_setup_runtime(
        hass, "entry", {}, [PromptApi(hass=hass, id="own", name="Own")]
    )

    instance = await async_get_llm_api(
        hass, hass.data[DOMAIN]["entry"], ["own", "assist"], LLM_CONTEXT
    )

    assert "own prompt" in instance.api_prompt
    assert "assist prompt" in instance.api_prompt


async def test_registered_apis_resolve_as_before(monkeypatch) -> None:
    hass = FakeHass()
    async_setup_runtime(hass, "entry", {})
    calls = []

    async def fake_async_get_api(**kwargs):
        calls.append(kwargs["api_id"])
        return "instance"

    monkeypatch.setattr(llm, "async_get_api", fake_async_get_api)

    assert (
        await async_get_llm_api(hass, hass.data[DOMAIN]["entry"], "assist", LLM_CONTEXT)
        == "instance"
    )
    assert calls == [["assist"]]


async def test_unknown_api_is_an_error() -> None:
    hass = FakeHass()
    async_setup_runtime(
        hass, "entry", {}, [PromptApi(hass=hass, id="own", name="Own")]
    )

    with pytest.raises(Exception, match="API missing not found"):
        await async_get_llm_api(
            hass, hass.data[DOMAIN]["entry"], ["own", "missing"], LLM_CONTEXT
        )


async def test_teardown_closes_sessions_and_drops_runtime() -> None:
    hass = FakeHass()
    async_setup_runtime(hass, "entry", {"api_key": "k"})
    session_manager = hass.data[DOMAIN]["entry"][GEMINI_SESSION_MANAGER_KEY]
    closed = []

    async def close_all() -> None:
        closed.append(True)

    session_manager.async_close_all = close_all

    await async_teardown_runtime(hass, "entry")
    await async_teardown_runtime(hass, "entry")

    assert closed == [True]
    assert "entry" not in hass.data[DOMAIN]


def test_runtime_is_not_set_up_twice() -> None:
    hass = FakeHass()
    async_setup_runtime(hass, "entry", {})

    with pytest.raises(ValueError, match="already set up"):
        async_setup_runtime(hass, "entry", {})


async def test_teardown_stops_running_turns() -> None:
    hass = FakeHass()
    async_setup_runtime(hass, "entry", {})
    session_manager = hass.data[DOMAIN]["entry"][GEMINI_SESSION_MANAGER_KEY]
    turn = asyncio.create_task(asyncio.Event().wait())
    session_manager._active_turn_tasks["conversation"] = turn

    await async_teardown_runtime(hass, "entry")

    assert turn.cancelled()
