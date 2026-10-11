# static-scaffold

Generates the `<name>-static` repos of zshsetup: vendored upstream projects as shallow submodules
under `vendor/`, a `build.sh` that builds with [zig](https://ziglang.org) as the C toolchain, smoke
tests, CI, and a release workflow. It also writes the workflows that open a pull request when
upstream publishes a new release.

## Prerequisites

- `uv`, which runs `copier` for the base files from
  [audivir/copier-template](https://github.com/audivir/copier-template)
- `git`, and `gh` to publish the created repo

## Installation

```shell
git clone https://github.com/zshsetup/static-scaffold
cd static-scaffold
uv sync
```

## Usage

Describe a project in `configs/<name>.toml`, see `configs/tmux.toml`, then create the repo:

```shell
uv run python -m static_scaffold new configs/tmux.toml --output ~/repos
```

The repo is created in `~/repos/tmux-static` with the submodules cloned. Review it, then publish
it with `gh repo create zshsetup/tmux-static --public --source . --push`.

Write the workflows that follow upstream releases into a checkout of a `-static` repo:

```shell
uv run python -m static_scaffold upstream ~/repos/tmux-static tmux
```

The projects and their tag patterns are listed in `static_scaffold/upstream.toml`. The workflows
need an `UPDATE_TOKEN` secret, a token of a user that may push to the repo and create releases,
because pull requests and releases of the default token start no workflows.

## License

MIT
