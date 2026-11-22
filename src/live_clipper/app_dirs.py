"""App-mode home directory resolution and preparation.

App mode is the packaged desktop usage. All relative paths in this codebase
are resolved against the process cwd, so app mode simply chdirs into the app
home before doing anything else. CLI usage in a project directory never calls
prepare_app_home and is unaffected.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

APP_DIR_NAME = "VenusTest"
OFFICIAL_APP_DIR_NAME = "Venus"
HOME_ENV_VAR = "LIVE_CLIPPER_HOME"

WORK_SUBDIRS = [
    Path("work") / "cache",
    Path("work") / "logs",
    Path("work") / "automation_state",
    Path("work") / "automation_logs",
    Path("work") / "service",
]


def _refuse_official_home(home: Path) -> Path:
    if home.name in {OFFICIAL_APP_DIR_NAME, f"{OFFICIAL_APP_DIR_NAME}-electron-runtime"}:
        raise RuntimeError("这是独立测试版，不能使用官方 Venus 的数据目录。")
    return home


def default_app_home() -> Path:
    override = os.environ.get(HOME_ENV_VAR, "").strip()
    if override:
        return _refuse_official_home(Path(override).expanduser())
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_DIR_NAME
    return Path.home() / ".live-clipper"


def default_output_root(home: Path) -> Path:
    # With an explicit home override (tests, portable setups), keep output
    # inside the home so nothing leaks into the real user profile.
    if os.environ.get(HOME_ENV_VAR, "").strip():
        return home / "output"
    if sys.platform == "darwin":
        return Path.home() / "Movies" / APP_DIR_NAME
    return home / "output"


def default_workspace_root(home: Path) -> Path:
    if os.environ.get(HOME_ENV_VAR, "").strip():
        return home / "workspace"
    if sys.platform == "darwin":
        return Path.home() / APP_DIR_NAME
    return home / "workspace"


def resolve_app_home(home: Path | None = None) -> Path:
    """Resolve the desktop App home without creating or changing anything."""
    return (home or default_app_home()).expanduser().resolve()


def prepare_app_home(home: Path | None = None) -> Path:
    home = resolve_app_home(home)
    for subdir in WORK_SUBDIRS:
        (home / subdir).mkdir(parents=True, exist_ok=True)
    (default_workspace_root(home) / "runs").mkdir(parents=True, exist_ok=True)
    return home
