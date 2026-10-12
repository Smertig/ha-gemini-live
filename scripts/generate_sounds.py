"""Generate the bundled response cues with Python's standard library.

Run once when changing the cues: python scripts/generate_sounds.py
The integration plays the generated WAV files; it does not synthesize at runtime.
"""

import math
from pathlib import Path
import struct
import wave

SAMPLE_RATE = 16000
PATTERNS = {
    "done": [(660, 0.10), (880, 0.15)],
}


def generate(output_dir: Path) -> None:
    """Write the softly enveloped 16 kHz mono PCM done cue."""
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, notes in PATTERNS.items():
        samples = [0] * int(SAMPLE_RATE * 0.02)
        for frequency, duration in notes:
            count = int(SAMPLE_RATE * duration)
            fade = int(SAMPLE_RATE * 0.015)
            for index in range(count):
                envelope = min(1.0, index / fade, (count - 1 - index) / fade)
                samples.append(
                    round(
                        7000
                        * envelope
                        * math.sin(2 * math.pi * frequency * index / SAMPLE_RATE)
                    )
                )
            samples.extend([0] * int(SAMPLE_RATE * 0.055))
        with wave.open(str(output_dir / f"{name}.wav"), "wb") as sound:
            sound.setnchannels(1)
            sound.setsampwidth(2)
            sound.setframerate(SAMPLE_RATE)
            sound.writeframes(struct.pack(f"<{len(samples)}h", *samples))


if __name__ == "__main__":
    generate(
        Path(__file__).resolve().parents[1] / "custom_components/gemini_live/sounds"
    )
