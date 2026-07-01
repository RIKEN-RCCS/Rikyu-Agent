"""Pure-local tests for config.download_dir() and config.resolve_local_dest().

No SSH, no network: everything is monkeypatched against a temp config file.
"""
import json
from pathlib import Path

import pytest

from rikyu_mcp import config


def _write_config(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data))


def test_download_dir_precedence(tmp_path, monkeypatch):
    cfg_dir_value = tmp_path / "cfg-download"
    env_dir_value = tmp_path / "env-download"
    cwd_value = tmp_path / "cwd-default"
    cwd_value.mkdir()

    config_file = tmp_path / "config.json"
    _write_config(config_file, {"local": {"download_dir": str(cfg_dir_value)}})
    monkeypatch.setattr(config, "CONFIG_PATH", config_file)

    # config-file value (no env var set)
    monkeypatch.delenv("RIKYU_DOWNLOAD_DIR", raising=False)
    assert config.download_dir() == cfg_dir_value.expanduser().resolve()

    # env var wins over config file
    monkeypatch.setenv("RIKYU_DOWNLOAD_DIR", str(env_dir_value))
    assert config.download_dir() == env_dir_value.expanduser().resolve()

    # cwd default when neither env var nor config-file value is present
    monkeypatch.delenv("RIKYU_DOWNLOAD_DIR", raising=False)
    empty_config_file = tmp_path / "empty_config.json"
    _write_config(empty_config_file, {})
    monkeypatch.setattr(config, "CONFIG_PATH", empty_config_file)
    monkeypatch.chdir(cwd_value)
    assert config.download_dir() == cwd_value.resolve()


def test_resolve_local_dest_basename(tmp_path, monkeypatch):
    download_dir_value = tmp_path / "downloads"
    config_file = tmp_path / "config.json"
    _write_config(config_file, {"local": {"download_dir": str(download_dir_value)}})
    monkeypatch.setattr(config, "CONFIG_PATH", config_file)
    monkeypatch.delenv("RIKYU_DOWNLOAD_DIR", raising=False)

    dest = config.resolve_local_dest("/remote/path/to/results.tar.gz", None)

    assert dest == (download_dir_value / "results.tar.gz").resolve()
    assert dest.parent.is_dir()


def test_resolve_local_dest_sandbox_escape(tmp_path, monkeypatch):
    download_dir_value = tmp_path / "downloads"
    outside_dir = tmp_path / "outside"
    config_file = tmp_path / "config.json"
    _write_config(config_file, {
        "local": {"download_dir": str(download_dir_value), "sandbox": True},
    })
    monkeypatch.setattr(config, "CONFIG_PATH", config_file)
    monkeypatch.delenv("RIKYU_DOWNLOAD_DIR", raising=False)

    with pytest.raises(ValueError):
        config.resolve_local_dest("/remote/file.txt", str(outside_dir / "file.txt"))
