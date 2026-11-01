"""Decode original activity ZIPs without extracting paths to the filesystem."""

from __future__ import annotations

import io
import zipfile
from typing import Any

from garmin_fit_sdk import Decoder, Stream

MAX_FIT_BYTES = 100 * 1024 * 1024


class UnsupportedActivity(ValueError):
    """The original activity did not contain a FIT file."""


def decode_activity(content: bytes) -> dict[Any, list[dict[Any, Any]]]:
    messages: dict[Any, list[dict[Any, Any]]] = {}
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        files = [info for info in archive.infolist() if info.filename.lower().endswith(".fit")]
        if not files:
            raise UnsupportedActivity("No FIT file in original activity ZIP")
        if sum(info.file_size for info in files) > MAX_FIT_BYTES:
            raise ValueError("FIT files exceed the size limit")
        for info in files:
            decoded, errors = Decoder(Stream.from_byte_array(bytearray(archive.read(info)))).read()
            if errors:
                raise ValueError("Garmin FIT decoder reported an error")
            for kind, entries in decoded.items():
                messages.setdefault(kind, []).extend(entries)
    return messages
