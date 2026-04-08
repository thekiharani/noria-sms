from __future__ import annotations

import tomllib
from pathlib import Path

import noria_messaging

ROOT = Path(__file__).resolve().parents[1]


def test_project_metadata_matches_noria_messaging_identity() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())

    assert pyproject["project"]["name"] == "noria-messaging"
    assert noria_messaging.__name__ == "noria_messaging"
    assert (ROOT / "src" / "noria_messaging").is_dir()


def test_legacy_noria_sms_egg_info_is_not_present() -> None:
    assert not (ROOT / "src" / "noria_sms.egg-info").exists()
