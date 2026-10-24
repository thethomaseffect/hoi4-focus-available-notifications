"""Copy one built mod into the Hearts of Iron IV local mods folder."""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from tools.paths import resolve_paths
from tools.targets import load_targets, repo_root


def _parse_remote_file_id(text: str) -> str | None:
    match = re.search(r'remote_file_id\s*=\s*"([^"]+)"', text)
    return match.group(1) if match else None


def _existing_remote_file_id(mods_dir: Path, slug: str) -> str | None:
    for path in (mods_dir / slug / "descriptor.mod", mods_dir / f"{slug}.mod"):
        if path.is_file():
            remote_id = _parse_remote_file_id(path.read_text(encoding="utf-8"))
            if remote_id:
                return remote_id
    return None


def _with_remote_file_id(text: str, remote_id: str | None) -> str:
    body = text.replace("\r\n", "\n")
    if not body.endswith("\n"):
        body += "\n"
    body = re.sub(r'remote_file_id\s*=\s*"[^"]+"\n?', "", body)
    if remote_id:
        body += f'remote_file_id="{remote_id}"\n'
    return body


def _with_path(text: str, path: str) -> str:
    body = text.replace("\r\n", "\n")
    if not body.endswith("\n"):
        body += "\n"
    body = re.sub(r'^path\s*=\s*"[^"]+"\n?', "", body, flags=re.MULTILINE)
    lines = body.splitlines(keepends=True)
    insert_at = len(lines)
    for index, line in enumerate(lines):
        if line.startswith("remote_file_id"):
            insert_at = index
            break
    lines.insert(insert_at, f'path="{path}"\n')
    return "".join(lines)


def _local_launcher_pointer(descriptor_text: str, dest: Path) -> str:
    pointer = _with_path(descriptor_text, dest.as_posix())
    pointer = re.sub(r'^remote_file_id\s*=\s*"[^"]+"\n?', "", pointer, flags=re.MULTILINE)
    match = re.search(r'^name="([^"]+)"', pointer, flags=re.MULTILINE)
    if match and not match.group(1).endswith(" (local)"):
        pointer = re.sub(
            r'^name="([^"]+)"',
            r'name="\1 (local)"',
            pointer,
            count=1,
            flags=re.MULTILINE,
        )
    return pointer


def deploy(keyword: str) -> Path:
    targets = load_targets()
    if keyword not in targets:
        known = ", ".join(sorted(targets))
        raise SystemExit(f"Unknown target {keyword!r}. Known targets: {known}")
    target = targets[keyword]
    source = repo_root() / "mods" / keyword
    if not (source / "descriptor.mod").is_file():
        raise SystemExit(f"Missing {source}. Run: python tools/build.py {keyword}")
    paths = resolve_paths()
    mods_dir = paths.mods
    mods_dir.mkdir(parents=True, exist_ok=True)
    dest = mods_dir / target.slug
    remote_id = _existing_remote_file_id(mods_dir, target.slug)
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(source, dest)
    descriptor_text = _with_remote_file_id(
        (source / "descriptor.mod").read_text(encoding="utf-8"),
        remote_id,
    )
    (dest / "descriptor.mod").write_text(descriptor_text, encoding="utf-8", newline="\n")
    pointer = _local_launcher_pointer(descriptor_text, dest)
    (mods_dir / f"{target.slug}.mod").write_text(pointer, encoding="utf-8", newline="\n")
    file_count = sum(1 for path in dest.rglob("*") if path.is_file())
    print(f"Updated {dest} ({file_count} files)")
    print(f"Updated {mods_dir / f'{target.slug}.mod'}")
    print("Enable the local copy in the playset. Its name ends with (local).")
    return dest


def main(argv: list[str] | None = None) -> int:
    targets = load_targets()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("keywords", nargs="+", choices=sorted(targets))
    args = parser.parse_args(argv)
    for keyword in args.keywords:
        deploy(keyword)
    return 0


if __name__ == "__main__":
    sys.exit(main())
