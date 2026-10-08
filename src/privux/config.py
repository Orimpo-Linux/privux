"""Persistent user choices: /etc/privux/privux.conf.

Only explicit choices are stored. Everything else falls back to the default of
the installed Privux version, so defaults can improve with updates.
"""

from __future__ import annotations

import configparser
import os
import tempfile
from pathlib import Path

from .options import OPTIONS, OPTIONS_BY_ID, _

CONFIG_PATH = "/etc/privux/privux.conf"
_HEADER = "# Privux configuration. Edit with `privux set` / `privux reset`.\n"


def _parser() -> configparser.ConfigParser:
    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str  # keep keys case-sensitive
    return parser


class Config:
    def __init__(self, root: Path | str = "/") -> None:
        self.path = Path(root) / CONFIG_PATH.lstrip("/")

    def load(self) -> dict[str, str]:
        parser = _parser()
        if self.path.exists():
            parser.read(self.path, encoding="utf-8")
        return dict(parser["options"]) if parser.has_section("options") else {}

    def save(self, overrides: dict[str, str]) -> None:
        parser = _parser()
        parser["options"] = dict(sorted(overrides.items()))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix=".privux-")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(_HEADER)
                parser.write(handle)
            os.chmod(tmp, 0o644)
            os.replace(tmp, self.path)
        except BaseException:
            try:
                os.unlink(tmp)
            except FileNotFoundError:
                pass
            raise


def effective_values(root: Path | str = "/") -> tuple[dict[str, str], list[str]]:
    """Return (value per option, warnings). Bad or unknown entries are ignored with a warning."""
    overrides = Config(root).load()
    values: dict[str, str] = {}
    warnings: list[str] = []
    for option in OPTIONS:
        raw = overrides.get(option.id)
        if raw is None:
            values[option.id] = option.default
            continue
        try:
            values[option.id] = option.normalize(raw)
        except ValueError as error:
            warnings.append(f"{CONFIG_PATH}: {error}; " + _("s'usa el valor per defecte"))
            values[option.id] = option.default
    for key in overrides:
        if key not in OPTIONS_BY_ID:
            warnings.append(f"{CONFIG_PATH}: " + _("opció desconeguda «{key}», s'ignora").format(key=key))
    return values, warnings
