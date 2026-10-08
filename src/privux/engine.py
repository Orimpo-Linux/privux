"""Plan, apply and check Privux options against a filesystem root.

Safety rules the engine follows:
* A file is "ours" if its content matches something Privux can render for that option,
  or if it carries the Privux marker in its first lines.
* Before overwriting a file that is not ours, the original is saved once as
  ``<file>.privux-orig``.
* A file that is not ours is never deleted.
* Post-change commands (systemctl, sysctl...) only run on the real system ("/"), never
  against a test root, and a failing command is reported as a warning, not an error.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from .options import MARKER, Option

BACKUP_SUFFIX = ".privux-orig"
_SEVERITY = {"ok": 0, "pending": 1, "modified": 2}


def host_path(root: Path | str, path: str) -> Path:
    return Path(root) / path.lstrip("/")


def _read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None


def _is_ours(option: Option, path: str, content: str) -> bool:
    if content in option.known_contents().get(path, set()):
        return True
    return MARKER in "\n".join(content.splitlines()[:5])


@dataclass
class FileAction:
    path: str
    action: str  # write | remove | unchanged | kept
    state: str  # ok | pending | modified
    backup: bool = False


def plan_option(option: Option, value: str, root: Path | str = "/") -> list[FileAction]:
    desired = option.render(value)
    actions: list[FileAction] = []
    for path in sorted(option.all_paths()):
        wanted = desired.get(path)
        target = host_path(root, path)
        current = _read(target)
        if wanted is None:
            if current is None:
                actions.append(FileAction(path, "unchanged", "ok"))
            elif _is_ours(option, path, current):
                actions.append(FileAction(path, "remove", "pending"))
            else:
                actions.append(FileAction(path, "kept", "ok"))
        elif current == wanted:
            actions.append(FileAction(path, "unchanged", "ok"))
        elif current is None:
            actions.append(FileAction(path, "write", "pending"))
        else:
            ours = _is_ours(option, path, current)
            backup_needed = not ours and not Path(str(target) + BACKUP_SUFFIX).exists()
            actions.append(FileAction(path, "write", "pending" if ours else "modified", backup_needed))
    return actions


def option_state(actions: list[FileAction]) -> str:
    return max((a.state for a in actions), key=_SEVERITY.__getitem__, default="ok")


@dataclass
class ApplyResult:
    option: str
    actions: list[FileAction]
    warnings: list[str] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        return any(a.action in ("write", "remove") for a in self.actions)


def _atomic_write(target: Path, content: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=target.parent, prefix=".privux-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
        os.chmod(tmp, 0o644)
        os.replace(tmp, target)
    except BaseException:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise


def apply_option(
    option: Option,
    value: str,
    root: Path | str = "/",
    *,
    dry_run: bool = False,
    run_post: bool = True,
) -> ApplyResult:
    actions = plan_option(option, value, root)
    result = ApplyResult(option.id, actions)
    if dry_run:
        return result

    desired = option.render(value)
    for action in actions:
        target = host_path(root, action.path)
        if action.action == "write":
            if action.backup:
                shutil.copy2(target, str(target) + BACKUP_SUFFIX)
            _atomic_write(target, desired[action.path])  # type: ignore[arg-type]
        elif action.action == "remove":
            target.unlink()

    if result.changed and run_post and Path(root) == Path("/"):
        for command in option.post:
            if shutil.which(command[0]) is None:
                result.warnings.append(f"{command[0]}: command not found")
                continue
            try:
                done = subprocess.run(command, capture_output=True, text=True, timeout=30)
            except (OSError, subprocess.TimeoutExpired) as error:
                result.warnings.append(f"{' '.join(command)}: {error}")
                continue
            if done.returncode != 0:
                detail = (done.stderr or done.stdout).strip().splitlines()
                result.warnings.append(f"{' '.join(command)}: {detail[-1] if detail else done.returncode}")
    return result
