from __future__ import annotations

import re
from pathlib import Path

import pytest

from live_clipper import app_dirs

ROOT = Path(__file__).resolve().parents[1]


def test_darwin_defaults_do_not_create_official_venus_directories(monkeypatch, tmp_path):
    monkeypatch.delenv(app_dirs.HOME_ENV_VAR, raising=False)
    monkeypatch.setattr(app_dirs.sys, "platform", "darwin")
    monkeypatch.setattr(app_dirs.Path, "home", lambda: tmp_path)

    home = app_dirs.prepare_app_home()
    assert home == tmp_path / "Library" / "Application Support" / "VenusTest"
    assert app_dirs.default_output_root(home) == tmp_path / "Movies" / "VenusTest"
    assert app_dirs.default_workspace_root(home) == tmp_path / "VenusTest"
    assert (home / "models").exists() is False
    for official in (
        tmp_path / "Library" / "Application Support" / "Venus",
        tmp_path / "Library" / "Application Support" / "Venus-electron-runtime",
        tmp_path / "Movies" / "Venus",
        tmp_path / "Venus",
    ):
        assert not official.exists()


def test_explicit_official_home_is_refused_before_any_write(monkeypatch, tmp_path):
    official = tmp_path / "Library" / "Application Support" / "Venus"
    monkeypatch.setenv(app_dirs.HOME_ENV_VAR, str(official))
    with pytest.raises(RuntimeError, match="官方 Venus"):
        app_dirs.default_app_home()
    assert not official.exists()


def test_unofficial_identity_is_unsigned_and_isolated_from_the_official_app():
    builder = (ROOT / "desktop/electron-builder.yml").read_text(encoding="utf-8")
    identity = (ROOT / "desktop/app-identity.js").read_text(encoding="utf-8")
    main = (ROOT / "desktop/main.js").read_text(encoding="utf-8")
    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")

    assert app_dirs.APP_DIR_NAME == "VenusTest"
    assert app_dirs.OFFICIAL_APP_DIR_NAME == "Venus"
    assert 'productName: "VenusTest"' in identity
    assert 'bundleId: "com.guozehong12.venustest"' in identity
    assert "updatesEnabled: false" in identity
    assert re.search(r"^appId: com\.guozehong12\.venustest$", builder, re.M)
    assert re.search(r"^productName: VenusTest$", builder, re.M)
    assert re.search(r"^  identity: null$", builder, re.M)
    assert re.search(r"^  notarize: false$", builder, re.M)
    assert "desktopAppHome" in main
    assert 'path.join(app.getPath("appData"), "Venus")' not in main
    assert license_text.startswith("MIT License")
    for path in (ROOT / "desktop").rglob("*"):
        if {"node_modules", "tests"} & set(path.parts) or not path.is_file() or path.suffix not in {".js", ".yml", ".sh"}:
            continue
        text = path.read_text(encoding="utf-8")
        assert "xattr" not in text
        assert "com.apple.quarantine" not in text
        assert "spctl --master-disable" not in text
