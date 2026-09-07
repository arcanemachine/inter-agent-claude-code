# inter-agent Claude Code setup

Read this only for first-time setup, setup failures, connect failures, or
name-conflict edge cases. Normal message handling and command routing live in
`SKILL.md`.

## Runtime wrapper

All skill commands call `<bin>/inter-agent-claude`, where `<bin>` is this skill's
absolute `bin/` directory. The wrapper finds the Python helper in this order:

1. `INTER_AGENT_CLAUDE_HELPER`, an exact executable path for development or
   emergency override.
2. `CLAUDE_PLUGIN_OPTION_PROJECT_PATH`, injected from the installed plugin's
   `project_path` config, using `<project_path>/.venv/bin/inter-agent-claude`.
3. The Claude-managed runtime helper at
   `~/.claude/data/inter-agent/venv/bin/inter-agent-claude` (or the root selected
   by `INTER_AGENT_CLAUDE_VENV`).
4. `inter-agent-claude` on PATH.

If plugin config provides `secret`, the wrapper exports it as
`INTER_AGENT_SECRET` before running the selected helper. If no helper resolves,
the wrapper reports a bounded setup-needed diagnostic on stdout and exits `3`.
If a helper or managed runtime is present but cannot run, it reports one bounded
source-specific diagnostic on stdout and exits `4`. The setup-needed remedy is
`/inter-agent setup`; an explicit helper or project-path failure must instead be
fixed or removed because managed setup does not modify overrides. Exit `127` is
reserved for a genuine shell command-not-found or exec race. Do not print the
`secret` or raw path/configuration contents.

## Clean installation

After adding and installing the plugin, restart Claude Code and run:

```text
/inter-agent setup
```

Setup is the only user-facing managed-runtime installation command. It creates or
repairs the Claude-managed virtual environment at:

```text
~/.claude/data/inter-agent/venv
```

It installs helper source `inter-agent-claude-code` `0.3.0` from the tagged
standalone archive selected by plugin release `0.2.4`:

```text
https://github.com/arcanemachine/inter-agent-claude-code/archive/refs/tags/inter-agent--v0.2.4.zip
```

Core `0.3.0` is installed from PyPI as the helper's exact runtime dependency
`inter-agent-core==0.3.0`.
The helper is Git-hosted rather than separately published to PyPI. Setup uses a
supported Python 3.10+ interpreter, `python -m venv`, and the managed
environment's `python -m pip`; installed users do not need `uv`.

Setup performs filesystem and network mutation. Before invoking it, explain the
destination, source, Python/venv requirement, and that endpoint and secret
discovery remain unchanged. Ask the user for explicit approval. Only after
approval, run:

```bash
<bin>/inter-agent-claude setup --yes
```

The wrapper and installer preserve the setup approval gate. Running setup
without `--yes` exits `2` without mutating anything. On successful setup, retry
an originally requested operation only if the setup result succeeded and the
user's request still calls for that operation. Do not invent an installation
success message when the command failed.

The installer accepts these explicit development/testing options:

```text
--source URL_OR_PATH
--venv PATH
--python PATH
--yes
```

The setup override variables are `INTER_AGENT_CLAUDE_SETUP_SOURCE` and
`INTER_AGENT_CLAUDE_SETUP_PYTHON`. External helper and project-path overrides
retain their precedence and are never modified by managed setup. No end-user
`uv` fallback, global pip, `sudo`, system package manager, or shell evaluation is
used.

## Repair and failure recovery

A missing managed venv is treated as a missing runtime. A managed venv directory
that exists but lacks a usable helper, has a non-executable helper, or has a
helper whose shebang interpreter is unavailable is treated as an incomplete
managed runtime. The wrapper points to `/inter-agent setup` for that case.

With explicit approval, setup may repair an incomplete managed venv using
`python -m venv --clear` only when the target is a real, non-symlink directory
containing `pyvenv.cfg`, the helper is known unusable, and the target is not an
unsafe ancestor such as `/`, the home directory, or a top-level system
directory. Missing targets are created without `--clear`; healthy targets are
reused without clearing. An existing symlink, file, unrecognized directory, or
unsafe path is refused for manual inspection and is never recursively cleared.
Setup may modify only the selected managed venv.

If Python 3.10+, venv support, ensurepip/pip, network access, or helper
verification is unavailable, setup fails with a bounded truthful diagnostic and
leaves overrides and shared inter-agent state unchanged. Ordinary installer
errors remain diagnostics from the installer; the wrapper's exit `3`/`4`
preflight messages are the one-line stdout notifications intended for Claude
Code Monitor. Successful protocol/status output remains stdout and ordinary
post-start helper diagnostics remain stderr.

For a valid inter-agent operation that fails after input validation, preserve the
original bounded diagnostic and tell the user to run `/inter-agent doctor
[optional context]`. This is a text-only recovery pointer: do not invoke doctor
or setup automatically, replace the original diagnostic, interpolate raw output
into a command, or expose secrets. If doctor fails, point back to this setup
file and the package-loading guidance rather than suggesting doctor recursively.

## Configure a local checkout

For development or a custom local core checkout, configure the installed plugin
`project_path` option to the checkout path, then prepare its venv:

```bash
cd /path/to/inter-agent-claude-code
uv sync --locked
```

The wrapper expects this helper:

```text
/path/to/inter-agent-claude-code/.venv/bin/inter-agent-claude
```

For one-off debugging, `INTER_AGENT_CLAUDE_HELPER=/path/to/inter-agent-claude`
overrides the plugin config. Fix or remove a broken override; `/inter-agent
setup` will not replace it.

## Shared runtime defaults

Setup does not change the shared bus endpoint, secret discovery, or data state.
Claude, Pi, and other hosts still use the normal inter-agent defaults unless
explicitly configured otherwise:

```text
127.0.0.1:16837
platform inter-agent state directory
```

The managed setup source is a stable tagged archive. It installs the helper
source and its exact Core dependency but does not publish or install a separate
Claude helper package from PyPI.

## Connect fallback

Try the persistent Monitor from `SKILL.md` first and wait for a connected line.
Do not use `status` or `list` as pre-checks.

Only if the **persistent** Monitor task exits without a connected or
already-connected line, run one fallback:

```bash
<bin>/inter-agent-claude status
```

- `connected=true` for your name: this session is already connected; stop.
- `connected=false`: connect again with a unique name.

Do not manually run `inter-agent-claude listen` in Bash.

## Name conflicts

The Claude listener retries one name conflict automatically:

```
[inter-agent] name "<name>" is already in use; retrying as "<name>-2".
```

Wait for the connected line under the retried name. If the retry also fails:

```
[inter-agent] name "<name>-2" is already in use after retry.
```

Then run `<bin>/inter-agent-claude list`, pick a unique name, and reconnect. If
a listener was killed with `kill -9` instead of `/inter-agent disconnect`, the
server may hold the name for up to ~40s; wait or choose a unique name.

## Persistent Monitor wrapper behavior

Empirically, Claude Code may render a persistent Monitor as two task entries: a
launcher wrapper that exits right after starting the listener (you may see
`Monitor "..." stream ended`) and the real persistent watch, which keeps
running.

Do not treat the wrapper exit as failure while the persistent task is still
running. Keep waiting for `[inter-agent] connected as "<name>"` or
`[inter-agent] already connected as "<name>"; no new listener started.` Only one
`inter-agent-claude listen` process actually runs.
