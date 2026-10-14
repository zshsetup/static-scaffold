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
it:

```shell
gh repo create zshsetup/tmux-static --public --source . --push
```

The repos of zshsetup share their settings, which the next commands copy from `tmux-static` to
a new repo. The first lets the update workflow merge its pull requests once the checks pass and
delete their branches, the second makes the checks required, and the others allow Actions to open
pull requests and turn on Dependabot alerts:

```shell
repo=zshsetup/NAME-static
gh api -X PATCH repos/$repo -F allow_auto_merge=true -F delete_branch_on_merge=true
gh api repos/zshsetup/tmux-static/rulesets --jq '.[0].id' \
  | xargs -I{} gh api repos/zshsetup/tmux-static/rulesets/{} \
  | jq 'del(.id,.source,.source_type,._links,.created_at,.updated_at,.node_id,.current_user_can_bypass)' \
  | gh api -X POST repos/$repo/rulesets --input -
gh api -X PUT repos/$repo/actions/permissions/workflow \
  -f default_workflow_permissions=read -F can_approve_pull_request_reviews=true
gh api -X PUT repos/$repo/vulnerability-alerts
```

`new` also writes the workflows that open a pull request when upstream publishes a new release,
using the `[upstream_tags]` table of the config. To rewrite them in an existing checkout, e.g. after
a change of the templates, run:

```shell
uv run python -m static_scaffold upstream ~/repos/tmux-static tmux
```

The tag patterns of all repos, also those without a config, are listed in
`static_scaffold/upstream.toml`. The workflows
need an `UPDATE_TOKEN` secret, a token of a user that may push to the repo and create releases,
because pull requests and releases of the default token start no workflows.

## Binary size

The archives of the generated repos are what users download, so a config can keep them small. These
are ways to do it, which a config uses where they pay off:

- Unused code can be dropped at link time (`-ffunction-sections -fdata-sections` with
  `-Wl,--gc-sections`, or `-Wl,-dead_strip` on macOS), as `configs/openssh.toml` does. For tmux,
  vim, and sqlite3 it saved only 3 to 8%, so their configs leave it out.
- Libraries are built without the parts the program does not use, e.g. OpenSSL in
  `configs/openssh.toml` has no DSA, legacy ciphers, or the other options it can do without.
- A program under a second name is a symlink to the first and not a copy, like `unpigz` of pigz.
  The archives keep symlinks, and pmg links them with `links` in the spec.
- Projects with several programs that would each embed the same large static library are linked
  into one multi-call binary, like BusyBox, whose symlinks run as the tool they are named after.
  `configs/openssh.toml` does this for OpenSSH: the unpacked archive shrinks from 62 MB to 9 MB,
  and the download from 24 MB to 4 MB.

For the multi-call binary, the objects of each program are linked together with the parts of
the project library they need, and all of their symbols but `main` are made local, as the programs
define globals with the same names. The renamed `main` functions are then linked once, with
a small dispatcher that looks at `basename(argv[0])`. The smoke tests cover the programs that
start each other by name, like `sshd` with `sshd-session`. This works for projects whose programs
are built from separate objects, and brings little where there is one program or the others are
small.

## License

MIT
