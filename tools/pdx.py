"""Paradox script reader. Brace structure is preserved so trigger blocks can be copied."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class ParseError(Exception):
    pass


@dataclass
class PdxObject:
    items: list[tuple[str | None, Any]] = field(default_factory=list)
    start: int = 0
    end: int = 0
    skipped_closers: int = 0
    unclosed: int = 0

    def get_all(self, key: str) -> list[Any]:
        return [value for item_key, value in self.items if item_key == key]

    def get(self, key: str) -> Any | None:
        values = self.get_all(key)
        return values[0] if values else None


def read_pdx_text(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _is_ident_char(char: str) -> bool:
    return char.isalnum() or char in {"_", ".", "-", ":", "@", "'"}


def tokenize(text: str) -> list[tuple[str, str, int, int]]:
    tokens: list[tuple[str, str, int, int]] = []
    index = 0
    length = len(text)
    while index < length:
        char = text[index]
        if char in " \t\r\n":
            index += 1
            continue
        if char == "#":
            while index < length and text[index] not in "\r\n":
                index += 1
            continue
        if char == '"':
            start = index
            index += 1
            while index < length and text[index] != '"':
                if text[index] == "\\" and index + 1 < length:
                    index += 2
                    continue
                index += 1
            if index < length:
                index += 1
            tokens.append(("string", text[start:index], start, index))
            continue
        if char == "{":
            tokens.append(("lbrace", char, index, index + 1))
            index += 1
            continue
        if char == "}":
            tokens.append(("rbrace", char, index, index + 1))
            index += 1
            continue
        if char == "=":
            tokens.append(("eq", char, index, index + 1))
            index += 1
            continue
        start = index
        if char in "<>":
            index += 1
            if index < length and text[index] == "=":
                index += 1
            tokens.append(("atom", text[start:index], start, index))
            continue
        while index < length and _is_ident_char(text[index]):
            index += 1
        if index == start:
            index += 1
            continue
        tokens.append(("atom", text[start:index], start, index))
    return tokens


def _line_of(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


class _Parser:
    def __init__(self, text: str, source: str):
        self.text = text
        self.source = source
        self.tokens = tokenize(text)
        self.index = 0
        self.unclosed = 0

    def peek(self) -> tuple[str, str, int, int] | None:
        if self.index >= len(self.tokens):
            return None
        return self.tokens[self.index]

    def pop(self) -> tuple[str, str, int, int]:
        if self.index >= len(self.tokens):
            raise ParseError(f"{self.source}: unexpected end of file")
        token = self.tokens[self.index]
        self.index += 1
        return token

    def parse_file(self) -> PdxObject:
        items: list[tuple[str | None, Any]] = []
        skipped = 0
        while self.peek() is not None:
            # A few shipped focus files have a spare closing brace after the last block.
            if self.peek()[0] == "rbrace":
                self.pop()
                skipped += 1
                continue
            items.append(self.parse_statement())
        return PdxObject(
            items=items,
            start=0,
            end=len(self.text),
            skipped_closers=skipped,
            unclosed=self.unclosed,
        )

    def parse_statement(self) -> tuple[str | None, Any]:
        kind, value, start, _end = self.pop()
        if kind == "rbrace":
            raise ParseError(f"{self.source}:{_line_of(self.text, start)}: unexpected '}}'")
        if kind == "lbrace":
            return None, self.parse_object(start)
        if self.peek() and self.peek()[0] == "eq":
            self.pop()
            return _unquote(value), self.parse_value()
        return None, _unquote(value)

    def parse_value(self) -> Any:
        token = self.peek()
        if token is None:
            raise ParseError(f"{self.source}: missing value at end of file")
        if token[0] == "lbrace":
            start = token[2]
            self.pop()
            return self.parse_object(start)
        _kind, value, _start, _end = self.pop()
        return _unquote(value)

    def parse_object(self, start: int) -> PdxObject:
        items: list[tuple[str | None, Any]] = []
        while True:
            token = self.peek()
            if token is None:
                # Some shipped focus files never close the last brace. Keep the contents.
                self.unclosed += 1
                return PdxObject(items=items, start=start, end=len(self.text))
            if token[0] == "rbrace":
                end = token[3]
                self.pop()
                return PdxObject(items=items, start=start, end=end)
            items.append(self.parse_statement())


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
        return value[1:-1]
    return value


def parse_pdx(text: str, source: str = "<text>") -> PdxObject:
    return _Parser(text, source).parse_file()


def parse_pdx_file(path: Path) -> tuple[str, PdxObject]:
    text = read_pdx_text(path)
    return text, parse_pdx(text, str(path))
