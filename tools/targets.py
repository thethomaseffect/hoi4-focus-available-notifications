"""Explicit mod targets. One keyword builds one notification mod."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Layer:
    kind: str
    workshop_id: str | None = None
    path: str | None = None


@dataclass(frozen=True)
class Target:
    keyword: str
    slug: str
    name: str
    dependencies: tuple[str, ...]
    layers: tuple[Layer, ...]
    id_prefix: str


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def targets_path() -> Path:
    return repo_root() / "targets.json"


def load_targets() -> dict[str, Target]:
    data = json.loads(targets_path().read_text(encoding="utf-8"))
    targets: dict[str, Target] = {}
    for keyword, raw in data.items():
        layers: list[Layer] = []
        for layer in raw["layers"]:
            layers.append(
                Layer(
                    kind=str(layer["kind"]),
                    workshop_id=layer.get("id"),
                    path=layer.get("path"),
                )
            )
        targets[keyword] = Target(
            keyword=keyword,
            slug=str(raw["slug"]),
            name=str(raw["name"]),
            dependencies=tuple(raw.get("dependencies") or []),
            layers=tuple(layers),
            id_prefix=str(raw["id_prefix"]),
        )
    return targets


def supported_workshop_ids(targets: dict[str, Target]) -> set[str]:
    found: set[str] = set()
    for target in targets.values():
        for layer in target.layers:
            if layer.kind == "workshop" and layer.workshop_id:
                found.add(str(layer.workshop_id))
    return found
