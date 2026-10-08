"""Command line interface: ``privux status|list|get|set|apply|reset``.

The future graphical panel is a thin layer over this tool, so everything the panel
needs is available here with ``--json``.

Exit codes: 0 ok, 1 status found pending/modified options, 2 bad usage,
3 root required, 4 runtime error.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from . import __version__
from .config import Config, effective_values
from .engine import apply_option, option_state, plan_option
from .options import OPTIONS, OPTIONS_BY_ID, _

EXIT_OK, EXIT_DRIFT, EXIT_USAGE, EXIT_ROOT, EXIT_ERROR = 0, 1, 2, 3, 4

STATE_LABEL = {
    "ok": _("correcte"),
    "pending": _("pendent d'aplicar"),
    "modified": _("fitxer modificat a mà"),
}
ACTION_LABEL = {
    "write": _("escrit"),
    "remove": _("eliminat"),
    "unchanged": _("sense canvis"),
    "kept": _("conservat (no és de Privux)"),
}
DRY_ACTION_LABEL = {
    "write": _("s'escriuria"),
    "remove": _("s'eliminaria"),
    "unchanged": _("sense canvis"),
    "kept": _("es conservaria (no és de Privux)"),
}


def _emit_json(data: object) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def _warn(message: str) -> None:
    print(f"privux: {message}", file=sys.stderr)


def _table(rows: list[tuple[str, ...]]) -> str:
    widths = [max(len(row[i]) for row in rows) for i in range(len(rows[0]))]
    return "\n".join("  ".join(cell.ljust(widths[i]) for i, cell in enumerate(row)).rstrip() for row in rows)


def _needs_root(args: argparse.Namespace) -> bool:
    return Path(args.root) == Path("/") and hasattr(os, "geteuid") and os.geteuid() != 0


def _resolve_ids(names: list[str]) -> list[str]:
    unknown = [n for n in names if n not in OPTIONS_BY_ID]
    if unknown:
        raise KeyError(unknown[0])
    return names or [o.id for o in OPTIONS]


# --------------------------------------------------------------------------- commands

def cmd_list(args: argparse.Namespace) -> int:
    values, warnings = effective_values(args.root)
    for w in warnings:
        _warn(w)
    if args.json:
        _emit_json(
            [
                {
                    "id": o.id,
                    "category": o.category,
                    "summary": o.summary,
                    "value": values[o.id],
                    "default": o.default,
                    "choices": list(o.choices),
                }
                for o in OPTIONS
            ]
        )
        return EXIT_OK
    rows = [(_("opció"), _("valor"), _("per defecte"), _("descripció"))]
    rows += [(o.id, values[o.id], o.default, o.summary) for o in OPTIONS]
    print(_table(rows))
    return EXIT_OK


def cmd_status(args: argparse.Namespace) -> int:
    values, warnings = effective_values(args.root)
    for w in warnings:
        _warn(w)
    entries = []
    for option in OPTIONS:
        actions = plan_option(option, values[option.id], args.root)
        entries.append((option, values[option.id], actions, option_state(actions)))
    all_ok = all(state == "ok" for *_rest, state in entries)

    if args.json:
        _emit_json(
            {
                "version": __version__,
                "ok": all_ok,
                "options": [
                    {
                        "id": o.id,
                        "category": o.category,
                        "summary": o.summary,
                        "value": value,
                        "default": o.default,
                        "is_default": value == o.default,
                        "choices": list(o.choices),
                        "state": state,
                        "files": [{"path": a.path, "state": a.state} for a in actions],
                    }
                    for o, value, actions, state in entries
                ],
            }
        )
    else:
        print(_("Privux {version}: estat de la privacitat").format(version=__version__))
        rows = [(o.id, value, _("(per defecte)") if value == o.default else "", STATE_LABEL[state])
                for o, value, _actions, state in entries]
        print(_table(rows))
        pending = sum(1 for *_rest, state in entries if state != "ok")
        if all_ok:
            print(_("Tot correcte."))
        else:
            print(_("{n} opcions no coincideixen amb la configuració. Executa: sudo privux apply").format(n=pending))
    return EXIT_OK if all_ok else EXIT_DRIFT


def cmd_get(args: argparse.Namespace) -> int:
    if args.option not in OPTIONS_BY_ID:
        raise KeyError(args.option)
    values, warnings = effective_values(args.root)
    for w in warnings:
        _warn(w)
    print(values[args.option])
    return EXIT_OK


def _apply_ids(args: argparse.Namespace, ids: list[str], values: dict[str, str]) -> int:
    labels = DRY_ACTION_LABEL if args.dry_run else ACTION_LABEL
    for option_id in ids:
        option = OPTIONS_BY_ID[option_id]
        result = apply_option(
            option, values[option_id], args.root, dry_run=args.dry_run, run_post=not args.no_reload
        )
        print(f"{option_id} = {values[option_id]}")
        for action in result.actions:
            suffix = _("  (original guardat com a .privux-orig)") if action.backup else ""
            print(f"  {labels[action.action]}: {action.path}{suffix}")
        for warning in result.warnings:
            _warn(f"{option_id}: {warning}")
    return EXIT_OK


def cmd_apply(args: argparse.Namespace) -> int:
    if not args.dry_run and _needs_root(args):
        _warn(_("cal executar-ho com a root (sudo privux apply)"))
        return EXIT_ROOT
    ids = _resolve_ids(args.options)
    values, warnings = effective_values(args.root)
    for w in warnings:
        _warn(w)
    return _apply_ids(args, ids, values)


def cmd_set(args: argparse.Namespace) -> int:
    option = OPTIONS_BY_ID.get(args.option)
    if option is None:
        raise KeyError(args.option)
    value = option.normalize(args.value)
    if _needs_root(args):
        _warn(_("cal executar-ho com a root (sudo privux set ...)"))
        return EXIT_ROOT
    config = Config(args.root)
    overrides = config.load()
    overrides[option.id] = value
    config.save(overrides)
    print(_("{id} = {value} (desat)").format(id=option.id, value=value))
    if args.no_apply:
        return EXIT_OK
    args.dry_run = False
    values, _warnings = effective_values(args.root)
    return _apply_ids(args, [option.id], values)


def cmd_reset(args: argparse.Namespace) -> int:
    if _needs_root(args):
        _warn(_("cal executar-ho com a root (sudo privux reset ...)"))
        return EXIT_ROOT
    ids = _resolve_ids(args.options)
    config = Config(args.root)
    overrides = config.load()
    for option_id in ids:
        overrides.pop(option_id, None)
    config.save(overrides)
    print(_("Valors per defecte restaurats: {ids}").format(ids=", ".join(ids)))
    args.dry_run = False
    values, _warnings = effective_values(args.root)
    return _apply_ids(args, ids, values)


# --------------------------------------------------------------------------- parser

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="privux",
        description=_("Eina de privacitat i hardening de Privux. Sense ordre, mostra l'estat."),
    )
    parser.add_argument("--version", action="version", version=f"privux {__version__}")
    parser.add_argument("--root", default=os.environ.get("PRIVUX_ROOT", "/"), help=argparse.SUPPRESS)
    sub = parser.add_subparsers(dest="command", metavar=_("ordre"))

    p = sub.add_parser("status", help=_("mostra si la configuració aplicada coincideix amb l'esperada"))
    p.add_argument("--json", action="store_true", help=_("sortida en JSON"))
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("list", help=_("llista les opcions, els valors actuals i els possibles"))
    p.add_argument("--json", action="store_true", help=_("sortida en JSON"))
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("get", help=_("mostra el valor d'una opció"))
    p.add_argument("option")
    p.set_defaults(func=cmd_get)

    p = sub.add_parser("set", help=_("canvia una opció i l'aplica (cal root)"))
    p.add_argument("option")
    p.add_argument("value")
    p.add_argument("--no-apply", action="store_true", help=_("desa el valor sense aplicar-lo"))
    p.add_argument("--no-reload", action="store_true", help=_("no reinicia serveis"))
    p.set_defaults(func=cmd_set)

    p = sub.add_parser("apply", help=_("aplica la configuració al sistema (cal root)"))
    p.add_argument("options", nargs="*", help=_("opcions concretes (per defecte, totes)"))
    p.add_argument("--dry-run", action="store_true", help=_("mostra què es faria sense tocar res"))
    p.add_argument("--no-reload", action="store_true", help=_("no reinicia serveis"))
    p.set_defaults(func=cmd_apply)

    p = sub.add_parser("reset", help=_("restaura els valors per defecte (cal root)"))
    p.add_argument("options", nargs="*", help=_("opcions concretes (per defecte, totes)"))
    p.add_argument("--no-reload", action="store_true", help=_("no reinicia serveis"))
    p.set_defaults(func=cmd_reset)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    raw = sys.argv[1:] if argv is None else list(argv)
    args = parser.parse_args(raw)
    if args.command is None:
        args = parser.parse_args([*raw, "status"])
    try:
        return args.func(args)
    except KeyError as error:
        names = ", ".join(o.id for o in OPTIONS)
        _warn(_("opció desconeguda «{name}». Opcions: {names}").format(name=error.args[0], names=names))
        return EXIT_USAGE
    except ValueError as error:
        _warn(str(error))
        return EXIT_USAGE
    except PermissionError as error:
        _warn(_("permís denegat: {path}").format(path=error.filename))
        return EXIT_ROOT
    except OSError as error:
        _warn(str(error))
        return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main())
