"""Check bundled sound assets and safe tool argument handling."""

import struct

import pytest

from gemini_live.sounds import SOUND_NAMES, async_sound_response, load_sound_pcm


def test_bundled_cues_are_distinct_short_non_silent_pcm():
    cues = [load_sound_pcm(name) for name in SOUND_NAMES]
    assert len(set(cues)) == len(SOUND_NAMES)
    for pcm in cues:
        assert 3200 < len(pcm) < 32000  # Between 100 ms and one second.
        samples = struct.unpack(f"<{len(pcm) // 2}h", pcm)
        assert 0 < max(abs(sample) for sample in samples) <= 7000
        assert samples[0] == samples[-1] == 0


@pytest.mark.parametrize("name", [None, "../ok", "missing", [], 1])
async def test_invalid_sound_call_returns_error_without_audio(name):
    pcm, result = await async_sound_response({"sound": name})
    assert pcm == b""
    assert "error" in result


async def test_missing_asset_returns_error_without_audio(monkeypatch):
    def missing(_name):
        raise FileNotFoundError("missing cue")

    monkeypatch.setattr("gemini_live.sounds.load_sound_pcm", missing)
    pcm, result = await async_sound_response({"sound": "ok"})
    assert pcm == b""
    assert "error" in result
