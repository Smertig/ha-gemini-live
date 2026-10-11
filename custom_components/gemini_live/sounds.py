"""Bundled nonverbal response sounds and the integration-owned model tool."""

import asyncio
from functools import lru_cache
from pathlib import Path
from typing import Any
import wave

from .live import LiveTool

SOUND_NAMES = ("ok", "done", "complete", "cancelled", "bad", "good")
PLAY_SOUND_TOOL_NAME = "play_sound"
PLAY_SOUND_TOOL = LiveTool(
    name=PLAY_SOUND_TOOL_NAME,
    description=(
        "Respond with a short nonverbal beep cue instead of speaking. "
        "ok: acknowledgement; done: an action succeeded; complete: a task finished; "
        "cancelled: cancellation; bad: failure or negative result; good: positive result. "
        "Call after any necessary Home Assistant actions, only when a sound is "
        "sufficient, and do not speak alongside it."
    ),
    parameters={
        "type": "object",
        "properties": {"sound": {"type": "string", "enum": list(SOUND_NAMES)}},
        "required": ["sound"],
    },
)
SOUND_INSTRUCTION = (
    "You may choose to respond with a short sound instead of speech by calling "
    "play_sound with ok, done, complete, cancelled, bad, or good. Use this for "
    "simple acknowledgements or action results when no explanation is needed, "
    "especially if the user requests a beep or nonverbal response. Perform the "
    "requested Home Assistant action first and choose a cue matching its actual "
    "result; never signal success before the action succeeds. Call play_sound "
    "before producing any speech, at most once per response, and do not speak "
    "afterwards. Answer questions needing information or explanation with speech. "
    "A cue does not end the conversation; use end_conversation separately when appropriate."
)


@lru_cache(maxsize=len(SOUND_NAMES))
def load_sound_pcm(name: str) -> bytes:
    """Load a fixed cue, with no user-supplied filesystem paths."""
    if name not in SOUND_NAMES:
        raise ValueError(f"Unknown sound; choose one of {', '.join(SOUND_NAMES)}")
    with wave.open(
        str(Path(__file__).with_name("sounds") / f"{name}.wav"), "rb"
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
    name = arguments.get("sound")
    if not isinstance(name, str) or name not in SOUND_NAMES:
        return b"", {"error": f"sound must be one of {', '.join(SOUND_NAMES)}"}
    try:
        pcm = await asyncio.to_thread(load_sound_pcm, name)
    except (OSError, ValueError, wave.Error) as exc:
        return b"", {"error": f"Could not load response sound: {exc}"}
    return pcm, {
        "success": True,
        "sound": name,
        "response_mode": "sound",
        "instruction": "Do not speak; the integration will play this cue.",
    }
