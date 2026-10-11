"""Tests of the subcommands."""

from __future__ import annotations

from typing import TYPE_CHECKING

from static_scaffold import cli

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def test_new_reports_the_created_repo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    seen: list[str] = []

    def fake_scaffold(unused_config: object, output: Path, org: str) -> Path:
        seen.append(org)
        return output / "tmux-static"

    monkeypatch.setattr(cli, "scaffold", fake_scaffold)
    config = tmp_path / "x.toml"
    config.write_text("")
    monkeypatch.setattr(cli, "load_config", lambda path: path.name)

    cli.new(config, tmp_path, "someorg")

    assert seen == ["someorg"]
    assert capsys.readouterr().out == f"scaffolded {tmp_path.resolve() / 'tmux-static'}\n"


def test_upstream_writes_the_workflows(tmp_path: Path) -> None:
    cli.upstream(tmp_path, "tmux")

    assert (tmp_path / ".github/workflows/upstream-update.yml").exists()
