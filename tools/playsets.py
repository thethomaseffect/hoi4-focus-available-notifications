"""Report playset mods that ship their own national focuses."""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from tools.focuses import load_focus_files
from tools.paths import GamePaths
from tools.targets import Target

REPLACE_PATH_RE = re.compile(r'replace_path\s*=\s*"([^"]+)"', re.IGNORECASE)
DEPENDENCY_RE = re.compile(r'dependencies\s*=\s*\{([^}]*)\}', re.IGNORECASE | re.DOTALL)
QUOTED_RE = re.compile(r'"([^"]+)"')


@dataclass
class PlaysetMod:
    playset: str
    playset_active: bool
    enabled: bool
    display_name: str
    steam_id: str | None
    dir_path: Path
    focus_files: list[Path]
    replace_national_focus: bool
    dependencies: list[str]


def _read_descriptor(folder: Path) -> str:
    path = folder / "descriptor.mod"
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def load_playset_mods(paths: GamePaths) -> list[PlaysetMod]:
    if not paths.launcher_db.is_file():
        raise FileNotFoundError(paths.launcher_db)
    conn = sqlite3.connect(f"file:{paths.launcher_db}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT p.name AS playset, p.isActive AS playset_active, pm.enabled,
                   m.displayName, m.steamId, m.dirPath
            FROM playsets_mods pm
            JOIN mods m ON m.id = pm.modId
            JOIN playsets p ON p.id = pm.playsetId
            ORDER BY p.name, pm.position
            """
        ).fetchall()
    finally:
        conn.close()

    mods: list[PlaysetMod] = []
    for row in rows:
        folder = Path(row["dirPath"]) if row["dirPath"] else Path()
        focus_dir = folder / "common" / "national_focus"
        focus_files = sorted(focus_dir.rglob("*.txt")) if focus_dir.is_dir() else []
        descriptor = _read_descriptor(folder)
        replace_paths = {item.replace("\\", "/") for item in REPLACE_PATH_RE.findall(descriptor)}
        dependency_match = DEPENDENCY_RE.search(descriptor)
        dependencies = QUOTED_RE.findall(dependency_match.group(1)) if dependency_match else []
        mods.append(
            PlaysetMod(
                playset=row["playset"],
                playset_active=bool(row["playset_active"]),
                enabled=bool(row["enabled"]),
                display_name=row["displayName"] or folder.name,
                steam_id=str(row["steamId"]) if row["steamId"] else None,
                dir_path=folder,
                focus_files=focus_files,
                replace_national_focus="common/national_focus" in replace_paths,
                dependencies=dependencies,
            )
        )
    return mods


def focus_mods(mods: list[PlaysetMod]) -> list[PlaysetMod]:
    return [mod for mod in mods if mod.focus_files or mod.replace_national_focus]


def is_supported_parent(mod: PlaysetMod, targets: dict[str, Target], workshop_ids: set[str]) -> bool:
    if mod.steam_id and mod.steam_id in workshop_ids:
        return True
    names = {target.name for target in targets.values()}
    names.update(dependency for target in targets.values() for dependency in target.dependencies)
    slugs = {target.slug for target in targets.values()}
    if mod.display_name in names:
        return True
    return mod.dir_path.name in slugs


def compare_to_targets(mod: PlaysetMod, targets: dict[str, Target], source_files: dict[str, dict[str, Path]]) -> list[str]:
    """Say whether an extra mod's focus file still matches a supported parent."""
    notes: list[str] = []
    for path in mod.focus_files:
        parent_name = None
        parent_path = None
        for keyword, files in source_files.items():
            match = files.get(path.name)
            if match is None:
                match = next((candidate for key, candidate in files.items() if Path(key).name == path.name), None)
            if match is not None:
                parent_name = keyword
                parent_path = match
                break
        if parent_path is None:
            notes.append(f"{path.name} does not replace a file in vanilla or owb")
            continue
        left = load_focus_files([path])
        right = load_focus_files([parent_path])
        left_ids = set(left.focuses)
        right_ids = set(right.focuses)
        changed = sorted(
            focus_id
            for focus_id in left_ids & right_ids
            if left.focuses[focus_id].signature() != right.focuses[focus_id].signature()
        )
        only_mod = sorted(left_ids - right_ids)
        only_parent = sorted(right_ids - left_ids)
        if not changed and not only_mod and not only_parent:
            notes.append(
                f"{path.name} matches the {parent_name} focus file aside from fields this mod ignores, such as cost"
            )
            continue
        sample = ", ".join((changed or only_mod or only_parent)[:8])
        notes.append(
            f"{path.name} differs from {parent_name}: "
            f"{len(changed)} changed, {len(only_mod)} only in this mod, {len(only_parent)} only in {parent_name}"
            + (f" ({sample})" if sample else "")
        )
    return notes
