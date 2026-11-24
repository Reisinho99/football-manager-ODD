"""Read-only index for Football Manager club logos from local graphics packs.

This module never attempts to identify a club by display name: the consumer
must provide a *verified native club UID*, not a Team UID. No HTTP endpoint,
FM process access or persistent account state is involved.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import xml.etree.ElementTree as ET


# FM graphics mapping example:
# <record from="12345" to="graphics/pictures/club/12345/logo"/>
_CLUB_LOGO = re.compile(r"^graphics/pictures/club/(\d+)/logo$", re.IGNORECASE)
_IMAGE_EXTENSIONS = (".png", ".webp", ".jpg", ".jpeg")


@dataclass(frozen=True)
class LogoIndex:
    logos: dict[str, Path]
    conflicts: frozenset[str]
    config_files: int
    rejected_records: int

    def resolve(self, club_uid: int | str | None) -> Path | None:
        """Return an unambiguous existing image, or None."""
        if club_uid is None or not str(club_uid).isdigit():
            return None
        uid = str(int(club_uid))
        if uid in self.conflicts:
            return None
        image = self.logos.get(uid)
        return image if image is not None and image.is_file() else None


def index_club_logos(graphics_root: str | Path) -> LogoIndex:
    """Recursively read TCM-style config.xml files under an explicit root.

    A record is accepted only when its destination is a club logo with the
    same numeric UID as its source filename. Ambiguous UIDs are suppressed.
    Paths outside the selected graphics root and malformed XML are ignored.
    """
    root = Path(graphics_root).expanduser().resolve()
    if not root.is_dir():
        return LogoIndex({}, frozenset(), 0, 0)
    found: dict[str, Path] = {}
    conflicts: set[str] = set()
    configs = rejected = 0
    for config in sorted(root.rglob("config.xml")):
        if not config.is_file():
            continue
        configs += 1
        try:
            document = ET.parse(config)
        except (ET.ParseError, OSError, ValueError):
            rejected += 1
            continue
        for record in document.iter("record"):
            target = (record.get("to") or "").replace("\\", "/").strip("/")
            match = _CLUB_LOGO.fullmatch(target)
            if not match:
                continue
            uid = str(int(match.group(1)))
            source = (record.get("from") or "").replace("\\", "/").strip()
            if not source or Path(source).is_absolute() or ".." in Path(source).parts:
                rejected += 1
                continue
            candidate = (config.parent / source).resolve()
            if not candidate.is_relative_to(root):
                rejected += 1
                continue
            if candidate.suffix.lower() in _IMAGE_EXTENSIONS:
                paths = (candidate,)
            else:
                paths = tuple(candidate.with_suffix(ext) for ext in _IMAGE_EXTENSIONS)
            actual = next((path for path in paths if path.is_file()), None)
            if actual is None:
                rejected += 1
                continue
            # Never accept a source pointing to a different numeric club ID.
            # Source names can contain subfolders, but must end in the UID.
            if actual.stem != uid:
                rejected += 1
                continue
            if uid in found and found[uid] != actual:
                conflicts.add(uid)
            else:
                found[uid] = actual
    for uid in conflicts:
        found.pop(uid, None)
    return LogoIndex(found, frozenset(conflicts), configs, rejected)
