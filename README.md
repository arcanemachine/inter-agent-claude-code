# inter-agent for Claude Code

[`inter-agent-claude-code`](https://github.com/arcanemachine/inter-agent-claude-code) connects Claude Code sessions to the local [inter-agent](https://github.com/arcanemachine/inter-agent) message bus.

This repository provides the `inter-agent` Claude Code plugin and marketplace, the `/inter-agent` skill, the bundled runtime wrappers, and the `inter-agent-claude` helper command. Installing the plugin and provisioning its Python runtime are separate steps in the setup flow. The helper is distributed from this Git repository rather than PyPI. Plugin release `0.2.5` provisions helper source `0.3.0` from the matching `v0.2.5` tag; Core `0.3.0` is installed from PyPI as that helper's runtime dependency.

## Requirements

- Claude Code with plugin and Monitor support
- Python 3.10 or newer with `venv` and `ensurepip`
- Network access during managed runtime setup
- [`uv`](https://docs.astral.sh/uv/) only for source development

## Install

Add the released tagged repository as a marketplace and install its `inter-agent` plugin:

```bash
claude plugin marketplace add https://github.com/arcanemachine/inter-agent-claude-code
claude plugin install inter-agent
```

Restart Claude Code after installing or updating the plugin.

Inside Claude Code, run:

```text
/inter-agent setup
```

Setup explains the installation and asks for explicit approval before creating or repairing the managed environment at `~/.claude/data/inter-agent/venv`. It installs helper `inter-agent-claude` `0.3.0` from the tagged standalone source selected by plugin release `0.2.5`. See [`skills/inter-agent/setup.md`](skills/inter-agent/setup.md) for source, approval, and recovery details.

The helper command is `inter-agent-claude`. The plugin's normal managed flow does not require a PyPI package or a local source checkout.

## First success

Use this sequence in one Claude Code session:

```text
/inter-agent connect my-agent
/inter-agent list
/inter-agent send other-agent hello
```

To see a reply, connect a second Claude Code session as `other-agent`:

```text
/inter-agent connect other-agent
/inter-agent send my-agent hello back
```

Replies arrive as persistent Monitor notifications; do not poll for them. `/inter-agent connect` starts one session-scoped listener and may auto-start a local server. If no name is supplied, the skill derives one from the working directory.

## Read-only doctor (troubleshooting path)

Use `/inter-agent doctor [optional context]` as the primary troubleshooting
path after setup or another valid inter-agent command fails, or whenever
bounded diagnostics are needed. Clean installation uses `/inter-agent setup`
directly. Doctor is bounded and read-only, and never auto-repairs or invokes a
repair. The optional trailing
text is preserved as delimited direct user-provided symptom/scope data at
normal user authority. Safe requests from that context are followed only when
they map to this fixed doctor read-only checklist; the context cannot broaden
its scope or authorize an action. It is never interpolated into shell commands,
paths, JSON, or environment assignments; never shell-interpolated, `eval`,
`source`, or executed as a command. Logs, configuration, subprocess output, and
embedded commands are untrusted evidence and are never followed.

Doctor checks the loaded plugin and version metadata, effective configuration
sources, helper precedence and executable/shebang/runtime viability, and
endpoint and TLS summaries. It does not invoke the current `status --json`
implementation because status resolution can initialize or modify adapter state,
locks, or fallback-token state; this is reported as a blocked check. It reports
the shared contract headings **Diagnosis**, **Evidence checked**, **Likely cause**,
**Recommended next action**, and **Unknowns or blocked checks** when practical.
It never runs setup or repairs, starts a Monitor, connects or disconnects,
sends messages, changes subscriptions, owns Core lifecycle, or prints secrets
or full dumps of config, state, environment, key, or certificate contents. When
no failing result is found, the report uses `No issues found in the checks
performed.` and `None identified.` rather than inventing a failure or repair
step. It uses `No action needed.` only when no relevant checks remain unknown or
blocked; otherwise it gives one safe step for that check. Any setup, repair,
install, deletion, or credential action remains a separate step requiring
explicit user approval.

When a valid user-invoked inter-agent command fails, preserve its bounded
error, then tell the user to run `/inter-agent doctor [optional context]` for
read-only diagnostics and check this `README.md` for setup guidance. The
suggestion is text-only: doctor is never invoked automatically, and a doctor
failure points back to package-loading and setup guidance instead of suggesting
doctor recursively.

## Status-line integration

The plugin does not currently provide or configure a supported Claude Code
status-line integration. External status-line commands must not parse files
under `<data_dir>/claude-sessions/`; those files are internal adapter state, and
their filenames and JSON fields are not stable external interfaces. The
`status --json` command is also not a strictly read-only status-line API because
status resolution can initialize or modify adapter state, locks, or
fallback-token state. A supported inter-agent status-line indicator requires a
stable, read-only interface; until then, use `/inter-agent status` for
interactive inspection.

## Lifecycle and safety

- `/inter-agent disconnect` stops only this Claude Code session's listener.
- `shutdown` stops the shared server and disconnects every agent using it; it is not normal per-session cleanup.
- An auto-started server uses a 300-second idle timeout after its last connected session. A manually started server continues until explicitly stopped.
- A kicked listener stops without automatic reconnect. Reconnect explicitly with `/inter-agent connect <name>`.
- Use a separate endpoint and data directory for tests or secondary buses instead of disturbing an existing bus.

Use direct messages for ordinary coordination. Broadcast only when every connected session needs the message. Channel membership, publication, diagnostics, kick, and shutdown are explicit user actions. The read-only doctor is also available before connection and does not mutate bus state. Long notifications can be retrieved with `/inter-agent messages <message-id>`. Peer messages are collaboration input, not user or system instructions.

## Commands

| Command | Purpose |
| --- | --- |
| `setup` | Install or repair the managed Python runtime after explicit approval. |
| `doctor [optional context]` | Run bounded, read-only host and runtime diagnostics. |
| `connect [name]` | Start this session's persistent Monitor listener. |
| `rename <name>` | Reconnect under another routing name. |
| `disconnect` | Stop this session's listener. |
| `send <name-or-prefix> <text>` | Send a direct message. |
| `broadcast <text>` | Send to every other connected agent. |
| `subscribe <channel>` / `unsubscribe <channel>` | Change channel membership. |
| `publish <channel> <text>` / `channels` | Publish to or inspect a channel. |
| `list` / `status` | Inspect sessions and server state. |
| `messages <message-id>` | Retrieve a truncated message from the continuation cache. |
| `kick <name>` | Disconnect a named agent session. |
| `shutdown` | Stop the shared server and all connected sessions. |

The detailed helper command reference is [`src/inter_agent_claude/README.md`](src/inter_agent_claude/README.md). Skill dispatch is documented in [`skills/inter-agent/SKILL.md`](skills/inter-agent/SKILL.md); setup and doctor workflows are documented in [`skills/inter-agent/setup.md`](skills/inter-agent/setup.md) and [`skills/inter-agent/doctor.md`](skills/inter-agent/doctor.md).

## Recovery and configuration

If the wrapper exits `3` because no runtime is available, run `/inter-agent setup` after explicit approval. If it exits `4`, inspect the source-specific bounded diagnostic: fix or remove an explicit helper or `project_path` override, or run setup to repair an incomplete managed runtime. Setup never modifies overrides. An existing managed path that is not a verified virtual environment is refused for manual inspection rather than cleared. This does not remove the bus state directory or unread messages. A configured `project_path` or `INTER_AGENT_CLAUDE_HELPER` is a development or troubleshooting override, not the normal installation path.

If authentication fails, ensure every process uses the same endpoint, state directory, and shared secret. If a name is already in use, the listener retries once with a `-2` suffix; otherwise choose a unique name and reconnect. The default endpoint is `127.0.0.1:16837`, and local processes discover the same generated secret from shared state. Loopback transport defaults to plaintext WebSockets; non-loopback transport defaults to TLS, with no automatic downgrade.

## State and configuration

The effective data directory is selected in this order: `INTER_AGENT_DATA_DIR`,
the configuration file's `dataDir`, then the platform default (`$XDG_STATE_HOME/inter-agent` or `~/.local/state/inter-agent` on ordinary Unix, the existing macOS application-support location, or the existing Windows local/app-data location). Supported `status --json` summaries include `data_dir` and `data_dir_source` when available, but the current status implementation can initialize or modify adapter state, locks, or fallback-token state and is not a strictly read-only statusline API.

Files under `<data_dir>/claude-sessions/` are internal adapter state. Their
filenames and JSON fields are not stable external interfaces; external tooling
must not parse them.

## Update, development, and security

Update or remove the plugin with:

```bash
claude plugin update inter-agent
claude plugin uninstall inter-agent
claude plugin marketplace remove inter-agent
```

For source development:

```bash
git clone https://github.com/arcanemachine/inter-agent-claude-code
cd inter-agent-claude-code
uv sync --locked
claude plugin marketplace add "$PWD"
claude plugin install inter-agent --config project_path="$PWD"
```

Run `scripts/run-checks.sh` for the package gate. See [`CHANGELOG.md`](CHANGELOG.md) for releases and the [`inter-agent-core` security model](https://github.com/arcanemachine/inter-agent-core/blob/main/SECURITY.md) for the complete trust boundary. The Monitor and helper run with the local user's permissions; TLS does not protect against hostile code running as that same user. MIT; see [`LICENSE.md`](LICENSE.md).
