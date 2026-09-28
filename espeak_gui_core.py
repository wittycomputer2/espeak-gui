"""Pure helpers for the eSpeak NG desktop application."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Language:
    default_voice: str
    accents: dict[str, str]


LANGUAGES: dict[str, Language] = {
    # eSpeak's native British English voice is ``en``.  Although ``en-gb`` is
    # accepted as an alias by some builds, variants such as ``+f2`` are not
    # applied consistently to that alias across packaged versions.
    "English": Language("en-us", {"American": "en-us", "British": "en"}),
    "Spanish": Language("es-mx", {"Mexican": "es-mx", "Spain": "es"}),
    "French": Language("fr", {}),
    "Japanese": Language("ja", {}),
    "Portuguese": Language("pt", {}),
}

GENDER_VARIANTS = {"Male": "m3", "Female": "f2"}

# Very low values passed through eSpeak's global pitch control can overwhelm the
# characteristics supplied by a female voice variant.  Keep the lower end of
# the female control useful while still allowing a noticeably deeper voice.
PITCH_LIMITS = {"Male": (0, 99), "Female": (55, 99)}


def voice_for(language: str, accent: str, gender: str) -> str:
    """Return the eSpeak voice expression for the selected controls."""
    details = LANGUAGES.get(language, LANGUAGES["English"])
    base_voice = details.accents.get(accent, details.default_voice)
    variant = GENDER_VARIANTS.get(gender, GENDER_VARIANTS["Male"])
    return f"{base_voice}+{variant}"


def pitch_limits(gender: str) -> tuple[int, int]:
    """Return the usable eSpeak pitch range for a displayed voice profile."""
    return PITCH_LIMITS.get(gender, PITCH_LIMITS["Male"])


def pitch_for(gender: str, pitch: int | float) -> int:
    """Clamp a pitch to the range that preserves the selected voice profile."""
    minimum, maximum = pitch_limits(gender)
    return max(minimum, min(maximum, int(pitch)))


def espeak_error(returncode: int, stderr: str) -> str | None:
    """Return an eSpeak diagnostic instead of allowing a silent fallback."""
    diagnostic = stderr.strip()
    if returncode != 0 or diagnostic:
        return diagnostic or f"eSpeak NG exited with status {returncode}."
    return None


def safe_recording_name(requested: str) -> str:
    """Turn a user-entered title into a safe MP3 filename."""
    name = requested.strip()
    if name.lower().endswith(".mp3"):
        name = name[:-4]
    name = re.sub(r"[^\w .()-]", "_", name, flags=re.UNICODE)
    name = re.sub(r"\s+", " ", name).strip(" .")
    if not name:
        raise ValueError("Please enter a filename.")
    return f"{name}.mp3"
