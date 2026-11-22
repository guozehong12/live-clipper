"""Locate the short WAV used to check a speech model.

PyInstaller does not package setuptools package data. The desktop build must
pass this file with --add-data, and a frozen process must look both beside this
module and under the extracted bundle root.
"""
from __future__ import annotations

import sys
import wave
from collections.abc import Iterator
from contextlib import contextmanager
from importlib import resources
from pathlib import Path

AUDIO_NAME = "validation_audio.wav"


class ValidationAudioUnavailable(FileNotFoundError):
    code = "validation_audio_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


def readable_wav(path: Path) -> bool:
    try:
        if not path.is_file() or path.stat().st_size < 44:
            return False
        with path.open("rb") as handle:
            header = handle.read(12)
        if header[:4] != b"RIFF" or header[8:12] != b"WAVE":
            return False
        with wave.open(str(path)) as audio:
            return (
                audio.getnchannels() > 0
                and audio.getsampwidth() > 0
                and audio.getframerate() > 0
                and audio.getnframes() > 0
            )
    except (OSError, wave.Error, EOFError):
        return False


def _stable_candidates() -> list[Path]:
    candidates = [Path(__file__).resolve().parent / AUDIO_NAME]
    frozen_root = getattr(sys, "_MEIPASS", None)
    if frozen_root:
        candidates.append(Path(frozen_root) / "live_clipper" / AUDIO_NAME)
    return candidates


@contextmanager
def open_validation_audio() -> Iterator[Path]:
    for candidate in _stable_candidates():
        if readable_wav(candidate):
            yield candidate
            return
    try:
        packaged = resources.files("live_clipper").joinpath(AUDIO_NAME)
        if packaged.is_file():
            with resources.as_file(packaged) as located:
                path = Path(located)
                if readable_wav(path):
                    yield path
                    return
    except (OSError, TypeError, ModuleNotFoundError, FileNotFoundError):
        pass
    raise ValidationAudioUnavailable()
