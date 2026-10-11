"""Renders the files of a `-static` repo and creates the repo."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import msgspec

from static_scaffold.models import Config, UpstreamEntry
from static_scaffold.upstream import write_workflows

TEMPLATES = Path(__file__).resolve().parent / "templates"

LINUX_RUNNERS = "          - os: ubuntu-latest\n"
MACOS_RUNNER = "          - os: macos-15\n"
LINUX_BUILDS = "          - os: ubuntu-latest\n            asset: linux-amd64"
BUILD_COMMAND = "./build.sh ${{ matrix.static && '--static' || '' }}"
MATRIX_JOB = "    runs-on: ${{ matrix.os }}"
APT_INSTALL = "sudo apt-get update && sudo apt-get install -y"


def run(args: list[str], cwd: Path | None = None, *, check: bool = True) -> int:
    """Runs a command found in PATH and returns its exit code, raising on failure if `check`."""
    executable = shutil.which(args[0])
    if executable is None:
        message = f"{args[0]} is not in PATH"
        raise SystemExit(message)
    command = [executable, *args[1:]]
    if check:
        subprocess.check_call(command, cwd=cwd)  # noqa: S603
        return 0
    return subprocess.call(command, cwd=cwd)  # noqa: S603


def read_template(name: str) -> str:
    """Returns the text of a template file."""
    return (TEMPLATES / name).read_text()


def render(text: str, values: dict[str, str]) -> str:
    """Replaces each `__KEY__` in the text by its value."""
    for key, value in values.items():
        text = text.replace(f"__{key}__", value)
    return text


def install_steps(config: Config) -> str:
    """Returns the CI steps that install the build tools of the config."""
    steps = ""
    for runner, command, packages in (
        ("Linux", APT_INSTALL, config.apt),
        ("macOS", "brew install", config.brew),
    ):
        if packages:
            steps += (
                f"      - name: Install build tools ({runner})\n"
                f"        if: runner.os == '{runner}'\n"
                f"        run: {command} {' '.join(packages)}\n"
            )
    return steps


def render_ci(config: Config) -> str:
    """Returns the CI workflow, limited to macOS for projects that only build there."""
    ci = render(read_template("ci.yml"), {"DEPS": install_steps(config)})
    if not config.macos_only:
        return ci
    ci = ci[: ci.index(LINUX_RUNNERS)] + ci[ci.index(MACOS_RUNNER) :]
    ci = ci[: ci.index("      - name: Test on CentOS 7")]
    ci = ci.replace(BUILD_COMMAND, "./build.sh")
    return ci.replace(
        "      - if: ${{ !matrix.static }}\n        run: ./tests/run_smoke_tests.sh",
        "      - run: ./tests/run_smoke_tests.sh",
    )


def render_release(config: Config) -> str:
    """Returns the release workflow, limited to macOS for projects that only build there."""
    release = render(
        read_template("release.yml"),
        {
            "DEPS": install_steps(config),
            "NAME": config.name,
            "MAIN": config.vendor[0].dir,
            "DIRS": config.dirs,
        },
    )
    if not config.macos_only:
        return release
    release = release[: release.index(LINUX_BUILDS)] + release[release.index(MATRIX_JOB) :]
    release = release.replace(BUILD_COMMAND, "./build.sh")
    release = release.replace("dist=\"dist${{ matrix.static && '-static' || '' }}\"", "dist=dist")
    return release.replace(
        "        if: matrix.asset == 'linux-amd64'\n",
        "        if: matrix.asset == 'macos-arm64'\n",
    )


def render_build(config: Config) -> str:
    """Returns build.sh from the head, the vendor preparation, the build, and the tail."""
    text = read_template("build_head.sh")
    text += "".join(f"prepare {vendor.dir}\n" for vendor in config.vendor) + "\n"
    if config.ncurses:
        text += read_template("ncurses.sh")
    text += config.build.strip("\n") + "\n"
    return text + render(
        read_template("build_tail.sh"), {"BIN": config.bin, "VERSION_CMD": config.version_cmd}
    )


def render_smoke_tests(config: Config) -> str:
    """Returns the smoke tests script with the tests of the config."""
    return render(
        read_template("smoke_tests.sh"), {"BIN": config.bin, "TESTS": config.tests.strip("\n")}
    )


def render_notice(config: Config) -> str:
    """Returns the NOTICE text with one block for each upstream project."""
    projects = "\n".join(
        f"{p.name}\n  {p.url}\n  Copyright (c) {p.copyright}\n  License: {p.license}\n"
        for p in config.project
    )
    return render(
        read_template("notice.txt"),
        {"BIN": config.bin, "NAME": config.name, "PROJECTS": projects},
    )


def render_license(config: Config) -> str:
    """Returns the MIT license text with a note that it excludes the upstream projects."""
    head = (
        "This license applies only to the code in this repository (build.sh, tests/, README.md,"
        " and\nrelated files). It does not apply to the upstream projects built by build.sh or to"
        f" the\n{config.bin} binaries built from them, which carry their own licenses"
        f" ({config.license_short}).\nSee NOTICE.\n\n"
    )
    return head + read_template("mit.txt")


def render_readme(config: Config) -> str:
    """Returns README.md with the projects listed in the acknowledgments."""
    acknowledgments = "\n".join(f"- [{p.name}]({p.url}) by {p.copyright}" for p in config.project)
    return render(
        read_template("readme.md"),
        {
            "NAME": config.name,
            "UPSTREAM": config.upstream,
            "EXTRA": config.extra,
            "PREREQ": config.prereq,
            "OUTPUTS": config.outputs,
            "MAIN": config.vendor[0].dir,
            "TAG": config.tag,
            "ACK": acknowledgments,
            "LICENSE_SHORT": config.license_short,
        },
    )


def add_vendors(root: Path, config: Config) -> None:
    """Clones each vendored project shallowly and registers it as a shallow submodule."""
    for vendor in config.vendor:
        dest = root / "vendor" / vendor.dir
        if not dest.exists():
            if vendor.commit:
                dest.mkdir(parents=True)
                run(["git", "init", "-q"], dest)
                run(["git", "remote", "add", "origin", vendor.url], dest)
                run(["git", "fetch", "-q", "--depth", "1", "origin", vendor.commit], dest)
                run(["git", "checkout", "-q", "FETCH_HEAD"], dest)
            else:
                clone = ["git", "clone", "-q", "--depth", "1", "--branch", vendor.tag]
                run([*clone, vendor.url, str(dest)])
        # the submodule may be registered already, which fails and changes nothing
        run(["git", "submodule", "add", "-q", vendor.url, f"vendor/{vendor.dir}"], check=False)
        key = f"submodule.vendor/{vendor.dir}.shallow"
        run(["git", "config", "-f", ".gitmodules", key, "true"])
    gitmodules = root / ".gitmodules"
    gitmodules.write_text(gitmodules.read_text().replace("\t", "    "))


def scaffold(config: Config, output: Path, org: str) -> Path:
    """Creates `<name>-static` below `output` and returns its root."""
    root = output / f"{config.name}-static"
    root.mkdir(parents=True, exist_ok=True)
    os.chdir(root)
    if not (root / ".git").exists():
        run(["git", "init", "-q", "-b", "main"])
    answers = {
        "project_name": f"{config.name}-static",
        "project_type": "shell",
        "publishable": "false",
        "description": config.description,
        "github_org": org,
    }
    run(
        ["uvx", "--quiet", "copier", "copy", "--defaults", "--trust", "--overwrite"]
        + ["gh:audivir/copier-template", "."]
        + [arg for key, value in answers.items() for arg in ("-d", f"{key}={value}")]
    )
    for directory in (".github/scripts", ".github/workflows", "tests", "vendor"):
        (root / directory).mkdir(parents=True, exist_ok=True)
    add_vendors(root, config)

    ignore = root / ".gitignore"
    if "build-static/" not in ignore.read_text():
        ignore.write_text(
            ignore.read_text()
            + "\n# build output\nbuild/\nbuild-static/\ndist/\ndist-static/\n*.log\n.zig-cache/\n"
        )
    (root / "VERSION").write_text(config.tag + "\n")
    scripts = {
        ".github/scripts/fetch-submodules.sh": read_template("fetch-submodules.sh"),
        "build.sh": render_build(config),
        "tests/run_smoke_tests.sh": render_smoke_tests(config),
    }
    for name, text in scripts.items():
        (root / name).write_text(text)
        (root / name).chmod(0o755)
    files = {
        ".github/workflows/ci.yml": render_ci(config),
        ".github/workflows/release.yml": render_release(config),
        "LICENSE": render_license(config),
        "NOTICE": render_notice(config),
        "README.md": render_readme(config),
    }
    for name, text in files.items():
        (root / name).write_text(text)
    if config.upstream_tags is not None:
        main = config.vendor[0]
        entry = UpstreamEntry(
            dir=main.dir,
            url=main.url,
            pattern=config.upstream_tags.pattern,
            release_sed=config.upstream_tags.release_sed,
        )
        write_workflows(root, config.name, entry)
    return root


def load_config(path: Path) -> Config:
    """Reads the TOML description of a `-static` repo."""
    return msgspec.toml.decode(path.read_bytes(), type=Config)


def write_summary(root: Path) -> None:
    """Prints the root of the created repo."""
    sys.stdout.write(f"scaffolded {root}\n")
