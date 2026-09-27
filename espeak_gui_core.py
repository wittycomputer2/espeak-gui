"""Pure helpers for the eSpeak NG desktop application."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Language:
    default_voice: str
    accents: dict[str, str]


LANGUAGES: dict[str, Language] = {
    "English": Language("en-us", {"American": "en-us", "British": "en-gb"}),
    "Spanish": Language("es-mx", {"Mexican": "es-mx", "Spain": "es"}),
    "French": Language("fr", {}),
    "Japanese": Language("ja", {}),
    "Portuguese": Language("pt", {}),
}

GENDER_VARIANTS = {"Male": "m3", "Female": "f3"}


def voice_for(language: str, accent: str, gender: str) -> str:
    """Return the eSpeak voice expression for the selected controls."""
    details = LANGUAGES.get(language, LANGUAGES["English"])
    base_voice = details.accents.get(accent, details.default_voice)
    variant = GENDER_VARIANTS.get(gender, GENDER_VARIANTS["Male"])
    return f"{base_voice}+{variant}"


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
