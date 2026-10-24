"""Build a notification mod for one explicit target keyword."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from tools.focuses import load_focus_files
from tools.generate import render_mod
from tools.paths import game_supported_version, resolve_paths
from tools.playsets import compare_to_targets, focus_mods, is_supported_parent, load_playset_mods
from tools.targets import load_targets, repo_root, supported_workshop_ids


def layer_focus_dir(kind: str, workshop_id: str | None, path: str | None, paths) -> Path:
    if kind == "install":
        return paths.install / "common" / "national_focus"
    if kind == "workshop":
        if not workshop_id:
            raise ValueError("workshop layer is missing an id")
        return paths.workshop / workshop_id / "common" / "national_focus"
    if kind == "path":
        if not path:
            raise ValueError("path layer is missing a path")
        root = Path(path)
        if not root.is_absolute():
            root = repo_root() / root
        nested = root / "common" / "national_focus"
        if nested.is_dir():
            return nested
        return root
    raise ValueError(f"unknown layer kind {kind}")


def collect_focus_files(target, paths) -> dict[str, Path]:
    chosen: dict[str, Path] = {}
    for layer in target.layers:
        folder = layer_focus_dir(layer.kind, layer.workshop_id, layer.path, paths)
        if not folder.is_dir():
            raise FileNotFoundError(f"{target.keyword}: national focus folder not found: {folder}")
        for file in folder.rglob("*.txt"):
            chosen[file.relative_to(folder).as_posix()] = file
    return chosen


def write_mod(target, paths) -> Path:
    source = collect_focus_files(target, paths)
    library = load_focus_files([source[key] for key in sorted(source)])
    version = game_supported_version(paths)
    rendered = render_mod(library, target, version)
    dest = repo_root() / "mods" / target.keyword
    if dest.exists():
        shutil.rmtree(dest)
    thumbnail = repo_root() / "assets" / target.keyword / "thumbnail.png"
    if not thumbnail.is_file():
        raise FileNotFoundError(
            f"Missing {thumbnail}. Add a 512x512 PNG or run python tools/make_placeholder_thumbnails.py"
        )
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "thumbnail.png").write_bytes(thumbnail.read_bytes())
    for relative, text in sorted(rendered.items()):
        target_path = dest / relative
        target_path.parent.mkdir(parents=True, exist_ok=True)
        if relative.endswith(".yml"):
            target_path.write_bytes(b"\xef\xbb\xbf" + text.encode("utf-8"))
        else:
            target_path.write_text(text, encoding="utf-8", newline="\n")
    active = sum(1 for focus in library.focuses.values() if not focus.skip_reason)
    print(
        f"{target.keyword}: {library.files_read} files, {len(library.trees)} trees, "
        f"{len(library.focuses)} focuses, {active} notified, wrote {dest}"
    )
    if library.warnings:
        print(f"{target.keyword}: {len(library.warnings)} warnings")
        for warning in library.warnings[:30]:
            print(f"  {warning}")
        if len(library.warnings) > 30:
            print(f"  ... {len(library.warnings) - 30} more")
    return dest


def report_playsets(targets, source_files: dict[str, dict[str, Path]]) -> int:
    paths = resolve_paths()
    try:
        mods = focus_mods(load_playset_mods(paths))
    except FileNotFoundError as exc:
        print(f"Could not read playsets: {exc}")
        return 0
    workshop_ids = supported_workshop_ids(targets)
    extras = [mod for mod in mods if not is_supported_parent(mod, targets, workshop_ids)]
    if not extras:
        print("Playsets: no unsupported mods with national focus files.")
        return 0
    print("Playsets: mods with national focus files that are not a build target:")
    for mod in extras:
        state = "enabled" if mod.enabled else "disabled"
        active = "active playset" if mod.playset_active else "inactive playset"
        print(f"- {mod.display_name} ({state}, {mod.playset}, {active})")
        if mod.dependencies:
            print(f"  dependencies: {', '.join(mod.dependencies)}")
        print(f"  folder: {mod.dir_path}")
        for note in compare_to_targets(mod, targets, source_files):
            print(f"  {note}")
    print("No extra notification mod was created. Say which of these should get one.")
    return len(extras)


def main(argv: list[str] | None = None) -> int:
    targets = load_targets()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("keywords", nargs="*", choices=sorted(targets))
    parser.add_argument("--list", action="store_true", help="print target keywords and exit")
    parser.add_argument("--playsets", action="store_true", help="only report unsupported focus mods")
    args = parser.parse_args(argv)
    if args.list:
        for keyword, target in targets.items():
            print(f"{keyword}: {target.name} -> mods/{keyword} ({target.slug})")
        return 0
    paths = resolve_paths()
    keywords = list(args.keywords)
    if args.playsets and not keywords:
        source_files = {keyword: collect_focus_files(target, paths) for keyword, target in targets.items()}
        report_playsets(targets, source_files)
        return 0
    if not keywords:
        parser.error("name at least one target: " + ", ".join(targets))
    for keyword in keywords:
        write_mod(targets[keyword], paths)
    source_files = {}
    for keyword, target in targets.items():
        try:
            source_files[keyword] = collect_focus_files(target, paths)
        except FileNotFoundError as exc:
            print(exc)
    report_playsets(targets, source_files)
    return 0


if __name__ == "__main__":
    sys.exit(main())
