"""Local Hearts of Iron IV folders. Nothing here is written into the mod."""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

STEAM_APP_ID = "394360"
GAME_FOLDER_NAME = "Hearts of Iron IV"
DOCUMENTS_GAME = Path("Paradox Interactive") / "Hearts of Iron IV"


@dataclass(frozen=True)
class GamePaths:
    documents: Path
    mods: Path
    launcher_db: Path
    workshop: Path
    install: Path

    @property
    def launcher_settings(self) -> Path:
        return self.install / "launcher-settings.json"


def _windows_documents() -> Path:
    home = Path.home()
    candidates = [
        home / "Documents",
        home / "OneDrive" / "Documents",
        Path(os.environ.get("USERPROFILE", str(home))) / "Documents",
    ]
    for candidate in candidates:
        documents_game = candidate / DOCUMENTS_GAME
        if documents_game.is_dir():
            return documents_game
    return home / "Documents" / DOCUMENTS_GAME


def _parse_vdf_paths(vdf_text: str) -> list[Path]:
    return [
        Path(match.group(1).replace("\\\\", "\\"))
        for match in re.finditer(r'"path"\s*"([^"]+)"', vdf_text)
    ]


def find_steam_libraries() -> list[Path]:
    libraries: list[Path] = []
    default_steam = Path(r"C:\Program Files (x86)\Steam")
    if sys.platform != "win32":
        default_steam = Path.home() / ".steam" / "steam"
    vdf = default_steam / "steamapps" / "libraryfolders.vdf"
    if vdf.is_file():
        libraries.extend(_parse_vdf_paths(vdf.read_text(encoding="utf-8", errors="replace")))
    if default_steam not in libraries:
        libraries.insert(0, default_steam)
    return libraries


def find_hoi4_install() -> Path:
    for library in find_steam_libraries():
        candidate = library / "steamapps" / "common" / GAME_FOLDER_NAME
        if candidate.is_dir() and (
            (candidate / "hoi4.exe").exists() or (candidate / "launcher-settings.json").exists()
        ):
            return candidate
    return Path(r"C:\Program Files (x86)\Steam\steamapps\common") / GAME_FOLDER_NAME


def find_workshop(install: Path) -> Path:
    steamapps = install.parent.parent
    workshop = steamapps / "workshop" / "content" / STEAM_APP_ID
    if workshop.is_dir():
        return workshop
    for library in find_steam_libraries():
        candidate = library / "steamapps" / "workshop" / "content" / STEAM_APP_ID
        if candidate.is_dir():
            return candidate
    return Path(r"C:\Program Files (x86)\Steam\steamapps\workshop\content") / STEAM_APP_ID


def resolve_paths() -> GamePaths:
    documents = _windows_documents()
    install = find_hoi4_install()
    return GamePaths(
        documents=documents,
        mods=documents / "mod",
        launcher_db=documents / "launcher-v2.sqlite",
        workshop=find_workshop(install),
        install=install,
    )


def game_supported_version(paths: GamePaths) -> str:
    settings = paths.launcher_settings
    if settings.is_file():
        try:
            data = json.loads(settings.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}
        raw = data.get("rawVersion")
        if raw:
            return str(raw)
    return "1.19.*"
