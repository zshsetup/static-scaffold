"""Tests of the upstream update workflows."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from static_scaffold.upstream import load_table, write_workflows

if TYPE_CHECKING:
    from pathlib import Path


def test_workflows_get_the_pattern_and_release_tag_rewrite(tmp_path: Path) -> None:
    write_workflows(tmp_path, "screen")

    update = (tmp_path / ".github/workflows/upstream-update.yml").read_text()
    release = (tmp_path / ".github/workflows/upstream-release.yml").read_text()

    assert "PATTERN: '^v\\.[0-9]+(\\.[0-9]+)+$'" in update
    assert "RELEASE_SED: 's/^v\\./v/'" in update
    assert "startsWith(github.event.head_commit.message, 'Update screen to ')" in release
    assert "__" not in update + release


def test_every_table_entry_has_a_pattern_that_excludes_pre_releases() -> None:
    table = load_table()

    assert len(table) >= 16
    for entry in table.values():
        assert entry.pattern.startswith("^")
        assert entry.pattern.endswith("$")


def test_unknown_project_raises(tmp_path: Path) -> None:
    with pytest.raises(KeyError):
        write_workflows(tmp_path, "no-such-project")
