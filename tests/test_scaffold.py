"""Tests of the rendering and the creation of -static repos."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from static_scaffold import scaffold as scaffold_module
from static_scaffold.scaffold import (
    load_config,
    render_build,
    render_ci,
    render_release,
    run,
    scaffold,
)
from static_scaffold.upstream import load_table

if TYPE_CHECKING:
    from static_scaffold.models import Config

CONFIGS = Path(__file__).resolve().parent.parent / "configs"


def test_macos_only_drops_linux_jobs_and_container_tests() -> None:
    config = load_config(CONFIGS / "btop.toml")
    ci = render_ci(config)
    release = render_release(config)

    assert "os: ubuntu" not in ci
    assert "Test on CentOS 7" not in ci
    assert "matrix.static" not in ci
    assert "asset: linux-amd64" not in release
    assert "if: matrix.asset == 'macos-arm64'" in release


def test_linux_projects_keep_every_job_and_install_build_tools() -> None:
    config = load_config(CONFIGS / "tmux.toml")
    ci = render_ci(config)

    assert "alpine:3.22" in ci
    assert "sudo apt-get update && sudo apt-get install -y autoconf automake" in ci
    assert "brew install autoconf automake" in ci
    assert "linux-musl-arm64" in render_release(config)


def test_release_ships_license_texts_of_the_vendored_projects() -> None:
    release = render_release(load_config(CONFIGS / "tmux.toml"))

    assert 'lic="$dist/share/licenses/tmux-static"' in release
    assert release.index("licenses/tmux-static") < release.index("tar -czf tmux-static-")


def test_ncurses_block_precedes_the_build_of_projects_that_need_it() -> None:
    with_ncurses = render_build(load_config(CONFIGS / "tmux.toml"))
    without = render_build(load_config(CONFIGS / "aha.toml"))

    assert with_ncurses.index("FALLBACKS=(") < with_ncurses.index('echo ">>> tmux"')
    assert "FALLBACKS=(" not in without
    assert "prepare tmux\nprepare libevent" in with_ncurses


def test_scaffold_writes_the_repo_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def record(args: list[str], *unused_args: object, **unused_kwargs: object) -> int:
        calls.append(args)
        root = tmp_path / "aha-static"
        # what copier and git would have created
        (root / ".gitmodules").write_text("[submodule]\n\tpath = x\n")
        (root / ".gitignore").write_text("*.pyc\n")
        return 0

    monkeypatch.setattr(scaffold_module, "run", record)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "aha-static").mkdir()

    root = scaffold(load_config(CONFIGS / "aha.toml"), tmp_path, "someorg")

    assert (root / "VERSION").read_text() == "0.5.1\n"
    assert (root / "build.sh").stat().st_mode & 0o111
    assert "build-static/" in (root / ".gitignore").read_text()
    assert "    path = x" in (root / ".gitmodules").read_text()
    copier = next(c for c in calls if "copier" in c)
    assert "github_org=someorg" in copier
    assert "project_name=aha-static" in copier
    assert next(c for c in calls if "submodule" in c)[:4] == ["git", "submodule", "add", "-q"]


def test_commit_vendors_are_fetched_instead_of_cloned(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[list[str]] = []

    def record(args: list[str], *unused_args: object, **unused_kwargs: object) -> int:
        calls.append(args)
        return 0

    monkeypatch.setattr(scaffold_module, "run", record)
    config = load_config(CONFIGS / "aha.toml")
    config.vendor[0].commit = "abc123"
    (tmp_path / ".gitmodules").write_text("")

    scaffold_module.add_vendors(tmp_path, config)

    assert ["git", "fetch", "-q", "--depth", "1", "origin", "abc123"] in calls
    assert not any(call[:2] == ["git", "clone"] for call in calls)


def test_run_raises_for_missing_command_and_returns_exit_code() -> None:
    with pytest.raises(SystemExit, match="no-such-command-xyz is not in PATH"):
        run(["no-such-command-xyz"])
    assert run(["false"], check=False) == 1
    assert run(["true"]) == 0
    with pytest.raises(Exception, match="returned non-zero"):
        run(["false"])


def test_config_defaults() -> None:
    config: Config = load_config(CONFIGS / "aha.toml")

    assert config.dirs == "bin share"
    assert config.macos_only is False


def test_existing_vendor_checkouts_and_repos_are_kept(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[list[str]] = []

    def record(args: list[str], *unused_args: object, **unused_kwargs: object) -> int:
        calls.append(args)
        return 0

    monkeypatch.setattr(scaffold_module, "run", record)
    monkeypatch.chdir(tmp_path)
    root = tmp_path / "aha-static"
    (root / ".git").mkdir(parents=True)
    (root / "vendor/aha").mkdir(parents=True)
    (root / ".gitmodules").write_text("")
    (root / ".gitignore").write_text("build-static/\n")

    config = load_config(CONFIGS / "aha.toml")
    config.upstream_tags = None

    scaffold(config, tmp_path, "zshsetup")

    assert not any(call[:2] in (["git", "clone"], ["git", "init"]) for call in calls)
    assert not (root / ".github/workflows/upstream-update.yml").exists()
    assert (root / ".gitignore").read_text() == "build-static/\n"


def test_new_writes_the_upstream_workflows_from_the_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def record(*unused_args: object, **unused_kwargs: object) -> int:
        return 0

    monkeypatch.setattr(scaffold_module, "run", record)
    monkeypatch.chdir(tmp_path)
    root = tmp_path / "tmux-static"
    root.mkdir()
    (root / ".gitmodules").write_text("")
    (root / ".gitignore").write_text("")

    scaffold(load_config(CONFIGS / "tmux.toml"), tmp_path, "zshsetup")

    update = (root / ".github/workflows/upstream-update.yml").read_text()
    assert "URL: https://github.com/tmux/tmux.git" in update
    assert "PATTERN: '^[0-9]+\\.[0-9]+[a-z]?$'" in update


def test_configs_and_the_upstream_table_agree() -> None:
    table = load_table()

    for path in CONFIGS.glob("*.toml"):
        config = load_config(path)
        assert config.upstream_tags is not None
        assert table[config.name].pattern == config.upstream_tags.pattern
        assert table[config.name].release_sed == config.upstream_tags.release_sed
        assert table[config.name].url == config.vendor[0].url
