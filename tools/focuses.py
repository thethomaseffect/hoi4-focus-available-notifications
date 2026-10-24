"""Read national focus files and describe when each focus can be started."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from tools.pdx import PdxObject, parse_pdx_file

FOCUS_KINDS = ("focus", "shared_focus", "joint_focus")
REFERENCE_KINDS = ("shared_focus", "joint_focus")
SAFE_ID = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_-]*$")
_CONSTANT_RE_CACHE: dict[str, re.Pattern[str]] = {}


@dataclass
class FocusDef:
    focus_id: str
    kind: str
    source_file: str
    prerequisite_groups: list[list[str]]
    raw_prerequisites: list[str]
    exclusive: list[str]
    raw_exclusive: list[str]
    available: str | None
    bypass: str | None
    allow_branch: str | None
    available_if_capitulated: bool
    skip_reason: str | None = None

    def signature(self) -> tuple[Any, ...]:
        return (
            self.skip_reason,
            tuple(tuple(group) for group in self.prerequisite_groups),
            tuple(self.raw_prerequisites),
            tuple(self.exclusive),
            tuple(self.raw_exclusive),
            _norm(self.available),
            _norm(self.bypass),
            _norm(self.allow_branch),
            self.available_if_capitulated,
        )


@dataclass
class TreeDef:
    tree_id: str
    sources: list[str] = field(default_factory=list)
    focus_ids: list[str] = field(default_factory=list)
    references: list[str] = field(default_factory=list)


@dataclass
class Library:
    focuses: dict[str, FocusDef]
    trees: dict[str, TreeDef]
    warnings: list[str]
    files_read: int

    def active_ids_for_tree(self, tree_id: str) -> list[str]:
        tree = self.trees[tree_id]
        active: list[str] = []
        for focus_id in tree.focus_ids:
            focus = self.focuses.get(focus_id)
            if focus and not focus.skip_reason:
                active.append(focus_id)
        return active


def _norm(text: str | None) -> str:
    if not text:
        return ""
    kept: list[str] = []
    for line in text.splitlines():
        comment = line.find("#")
        if comment >= 0:
            line = line[:comment]
        kept.append(line)
    return " ".join(" ".join(kept).split())


def _substitute(text: str, constants: list[tuple[str, str]]) -> str:
    if not constants or "@" not in text:
        return text
    current = text
    for _ in range(5):
        updated = current
        for name, value in constants:
            pattern = _CONSTANT_RE_CACHE.get(name)
            if pattern is None:
                pattern = re.compile(rf"(?<![A-Za-z0-9_]){re.escape(name)}(?![A-Za-z0-9_])")
                _CONSTANT_RE_CACHE[name] = pattern
            updated = pattern.sub(lambda _match, replacement=value: replacement, updated)
        if updated == current:
            break
        current = updated
    return current


def _file_constants(root: PdxObject) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for key, value in root.items:
        if key and key.startswith("@") and isinstance(value, str):
            found.append((key, value))
    found.sort(key=lambda item: len(item[0]), reverse=True)
    return found


def _body(text: str, node: PdxObject, constants: list[tuple[str, str]]) -> str | None:
    raw = text[node.start + 1 : node.end - 1]
    raw = raw.replace("\r\n", "\n").replace("\r", "\n")
    raw = _substitute(raw, constants)
    if not raw.strip():
        return None
    return raw.strip("\n")


def _focus_lists(
    node: PdxObject,
    text: str,
    constants: list[tuple[str, str]],
    label: str,
    context: str,
    warnings: list[str],
) -> tuple[list[list[str]], list[str]]:
    groups: list[list[str]] = []
    raw_blocks: list[str] = []
    for block in node.get_all(label):
        if not isinstance(block, PdxObject):
            warnings.append(f"{context}: {label} is not a block")
            continue
        ids: list[str] = []
        extra = False
        for key, value in block.items:
            if key and key.lower() == "focus" and isinstance(value, str) and value:
                ids.append(value)
            elif key is not None:
                extra = True
        if extra:
            body = _body(text, block, constants)
            if body:
                raw_blocks.append(_rewrite_focus_keys(body))
                warnings.append(f"{context}: {label} block contains more than focus ids")
        elif ids:
            groups.append(ids)
    return groups, raw_blocks


def _rewrite_focus_keys(body: str) -> str:
    return re.sub(
        r"(?<![A-Za-z0-9_])focus(\s*=\s*)([A-Za-z0-9_-]+)",
        r"has_completed_focus\1\2",
        body,
        flags=re.IGNORECASE,
    )


def _combined_trigger(
    node: PdxObject,
    key: str,
    text: str,
    constants: list[tuple[str, str]],
    context: str,
    warnings: list[str],
) -> str | None:
    """Duplicate trigger blocks are all required. An empty block adds nothing."""
    bodies: list[str] = []
    for block in node.get_all(key):
        if not isinstance(block, PdxObject):
            continue
        body = _body(text, block, constants)
        if body is None:
            continue
        normalized = _norm(body)
        if normalized in {"always = yes", "always=yes"}:
            continue
        if key == "bypass" and normalized == "always = no":
            continue
        bodies.append(body)
    if not bodies:
        return None
    if len(bodies) > 1:
        warnings.append(f"{context}: {key} is defined more than once; all blocks are required")
    return "\n".join(bodies)


def _capitulated_ok(node: PdxObject) -> bool:
    value = node.get("available_if_capitulated")
    return isinstance(value, str) and value.lower() == "yes"


def _parse_focus(
    node: PdxObject,
    kind: str,
    text: str,
    constants: list[tuple[str, str]],
    source_file: str,
    warnings: list[str],
) -> FocusDef | None:
    focus_id = node.get("id")
    if not isinstance(focus_id, str) or not focus_id:
        warnings.append(f"{source_file}: {kind} block without an id")
        return None
    if not SAFE_ID.match(focus_id):
        warnings.append(f"{source_file}: skipping focus id {focus_id!r}")
        return None
    groups, raw_prereq = _focus_lists(node, text, constants, "prerequisite", focus_id, warnings)
    exclusive, raw_exclusive = _focus_lists(node, text, constants, "mutually_exclusive", focus_id, warnings)
    flat_exclusive: list[str] = []
    for group in exclusive:
        for item in group:
            if item != focus_id and item not in flat_exclusive:
                flat_exclusive.append(item)
    available = _combined_trigger(node, "available", text, constants, focus_id, warnings)
    bypass = _combined_trigger(node, "bypass", text, constants, focus_id, warnings)
    allow_branch = _combined_trigger(node, "allow_branch", text, constants, focus_id, warnings)
    skip_reason = None
    if _norm(allow_branch) == "always = no":
        skip_reason = "allow_branch always no"
        allow_branch = None
    elif _norm(available) == "always = no":
        skip_reason = "available always no"
        available = None
    elif _norm(bypass) == "always = yes":
        skip_reason = "bypass always yes"
        bypass = None
    if _norm(bypass) == "always = no":
        bypass = None
    return FocusDef(
        focus_id=focus_id,
        kind=kind,
        source_file=source_file,
        prerequisite_groups=groups,
        raw_prerequisites=raw_prereq,
        exclusive=flat_exclusive,
        raw_exclusive=raw_exclusive,
        available=available,
        bypass=bypass,
        allow_branch=allow_branch,
        available_if_capitulated=_capitulated_ok(node),
        skip_reason=skip_reason,
    )


def load_focus_files(files: list[Path]) -> Library:
    focuses: dict[str, FocusDef] = {}
    trees: dict[str, TreeDef] = {}
    warnings: list[str] = []
    pending_refs: list[tuple[str, str, str]] = []

    def remember(focus: FocusDef) -> None:
        previous = focuses.get(focus.focus_id)
        if previous and previous.signature() != focus.signature():
            warnings.append(
                f"{focus.focus_id} is defined in {previous.source_file} and again in {focus.source_file}"
            )
        elif previous and previous.source_file != focus.source_file:
            warnings.append(
                f"{focus.focus_id} is defined in both {previous.source_file} and {focus.source_file}"
            )
        focuses[focus.focus_id] = focus

    def tree_for(tree_id: str, source_file: str) -> TreeDef:
        tree = trees.get(tree_id)
        if tree is None:
            tree = TreeDef(tree_id=tree_id)
            trees[tree_id] = tree
        if source_file not in tree.sources:
            tree.sources.append(source_file)
        return tree

    for path in files:
        text, root = parse_pdx_file(path)
        source_file = path.name
        if root.skipped_closers:
            warnings.append(f"{source_file}: ignored {root.skipped_closers} extra closing brace(s)")
        if root.unclosed:
            warnings.append(f"{source_file}: closed {root.unclosed} unclosed brace(s) at end of file")
        constants = _file_constants(root)
        for key, value in root.items:
            if key in ("shared_focus", "joint_focus") and isinstance(value, PdxObject):
                parsed = _parse_focus(value, key, text, constants, source_file, warnings)
                if parsed:
                    remember(parsed)
            elif key == "focus" and isinstance(value, PdxObject):
                warnings.append(f"{source_file}: top-level focus block {value.get('id')}")
        for key, value in root.items:
            if key != "focus_tree" or not isinstance(value, PdxObject):
                continue
            tree_id = value.get("id")
            if not isinstance(tree_id, str) or not SAFE_ID.match(tree_id):
                warnings.append(f"{source_file}: focus tree has no usable id")
                continue
            tree = tree_for(tree_id, source_file)
            for child_key, child in value.items:
                if child_key in FOCUS_KINDS and isinstance(child, PdxObject):
                    parsed = _parse_focus(child, child_key, text, constants, source_file, warnings)
                    if not parsed:
                        continue
                    remember(parsed)
                    if parsed.focus_id not in tree.focus_ids:
                        tree.focus_ids.append(parsed.focus_id)
                elif child_key in REFERENCE_KINDS and isinstance(child, str) and child:
                    pending_refs.append((tree_id, child, source_file))
                    if child not in tree.references:
                        tree.references.append(child)

    for tree_id, focus_id, source_file in pending_refs:
        tree = tree_for(tree_id, source_file)
        focus = focuses.get(focus_id)
        if focus is None:
            warnings.append(f"{source_file}: {tree_id} references unknown focus {focus_id}")
            continue
        if focus_id not in tree.focus_ids:
            tree.focus_ids.append(focus_id)
    return Library(focuses=focuses, trees=trees, warnings=warnings, files_read=len(files))
