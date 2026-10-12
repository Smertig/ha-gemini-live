"""Bundled nonverbal response sounds and the integration-owned model tool."""

import asyncio
from functools import lru_cache
from pathlib import Path
from typing import Any
import wave

from .live import LiveTool

PLAY_SOUND_TOOL_NAME = "play_sound"
PLAY_SOUND_TOOL = LiveTool(
    name=PLAY_SOUND_TOOL_NAME,
    description=(
        "Play the done cue instead of speaking and end the conversation. "
        "Call only after the requested action succeeds and no explanation is needed."
    ),
    parameters={
        "type": "object",
        "properties": {},
        "additionalProperties": False,
    },
)
SOUND_INSTRUCTION = (
    "You may choose to respond with a short sound instead of speech by calling "
    "play_sound with no arguments. It plays the done cue and ends the conversation. "
    "Use it for successful action results when no explanation is needed, "
    "especially if the user requests a beep or nonverbal response. Perform the "
    "requested Home Assistant action first; never signal success before the "
    "action succeeds. Call play_sound "
    "before producing any speech, at most once per response, and do not speak "
    "afterwards. Answer questions needing information or explanation with speech. "
)


@lru_cache(maxsize=1)
def load_sound_pcm() -> bytes:
    """Load a fixed cue, with no user-supplied filesystem paths."""
    with wave.open(
        str(Path(__file__).with_name("sounds") / "done.wav"), "rb"
    ) as sound:
        if (
            sound.getnchannels(),
            sound.getsampwidth(),
            sound.getframerate(),
            sound.getcomptype(),
        ) != (1, 2, 16000, "NONE"):
            raise ValueError("Response sounds must be 16 kHz mono PCM WAV files")
        return sound.readframes(sound.getnframes())


async def async_sound_response(
    arguments: dict[str, Any],
) -> tuple[bytes, dict[str, Any]]:
    """Resolve a sound tool call without blocking the event loop."""
    if arguments:
        return b"", {"error": "play_sound takes no arguments"}
    try:
        pcm = await asyncio.to_thread(load_sound_pcm)
    except (OSError, ValueError, wave.Error) as exc:
        return b"", {"error": f"Could not load response sound: {exc}"}
    return pcm, {
        "success": True,
        "sound": "done",
        "conversation_ended": True,
        "response_mode": "sound",
        "instruction": (
            "Do not speak; the integration will play the done cue and end the conversation."
        ),
    }
