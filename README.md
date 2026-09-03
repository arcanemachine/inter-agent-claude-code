# inter-agent for Claude Code

[`inter-agent-claude-code`](https://github.com/arcanemachine/inter-agent-claude-code) connects Claude Code sessions to the local [inter-agent](https://github.com/arcanemachine/inter-agent) message bus.

This repository provides the `inter-agent` Claude Code plugin and marketplace, the `/inter-agent` skill, the bundled runtime wrappers, and the `inter-agent-claude` helper command. Installing the plugin and provisioning its Python runtime are separate steps in the setup flow. The helper is distributed from this Git repository rather than PyPI. Plugin release `0.2.3` provisions helper source `0.3.0` from the matching `inter-agent--v0.2.3` tag; Core `0.3.0` is installed from PyPI as that helper's runtime dependency.

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
/inter-agent bootstrap
```

Bootstrap explains the installation and asks for explicit approval. It creates the managed environment at `~/.claude/data/inter-agent/venv` and installs helper `inter-agent-claude` `0.3.0` from the tagged standalone source selected by the plugin release. See [`skills/inter-agent/bootstrap.md`](skills/inter-agent/bootstrap.md) for the source and recovery details.

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

## Read-only doctor

Run `/inter-agent doctor [optional context]` to get a bounded, host-native
diagnostic before connecting or when setup is unavailable. The optional trailing
text is preserved as delimited direct user-provided symptom/scope data at
normal user authority. Safe requests from that context are followed only when
they map to this fixed doctor read-only checklist; the context cannot broaden
its scope or authorize an action. It is never interpolated into shell commands,
paths, JSON, or environment assignments; never shell-interpolated, `eval`,
`source`, or executed as a command. Logs, configuration, subprocess output, and
embedded commands are untrusted evidence and are never followed.

Doctor checks the loaded plugin and version metadata, effective configuration
sources, helper precedence and executable/shebang/runtime viability, endpoint
and TLS summaries, and (only when explicitly confirmed non-initializing and
non-mutating) a single bounded `status --json` result. It reports the shared
contract headings **Diagnosis**, **Evidence checked**, **Likely cause**,
**Recommended next action**, and **Unknowns or blocked checks** when practical.
It never bootstraps or repairs, starts a Monitor, connects or disconnects,
sends messages, changes subscriptions, owns Core lifecycle, or prints secrets
or full dumps of config, state, environment, key, or certificate contents. Any
bootstrap, repair, install, deletion, or credential action remains a separate
step requiring explicit user approval.

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
| `bootstrap` | Install or repair the managed Python runtime. |
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

The detailed helper command reference is [`src/inter_agent_claude/README.md`](src/inter_agent_claude/README.md). Skill behavior and setup recovery are documented in [`skills/inter-agent/SKILL.md`](skills/inter-agent/SKILL.md) and [`skills/inter-agent/bootstrap.md`](skills/inter-agent/bootstrap.md).

## Recovery and configuration

If the wrapper exits `127` with setup needed, run `/inter-agent doctor` first for read-only evidence, then run `/inter-agent bootstrap` only after explicit approval. Doctor may recommend removing a stale managed environment or another repair, but never performs that action. If the managed environment is missing or stale, remove only `~/.claude/data/inter-agent/venv` and bootstrap again; this does not remove the bus state directory or unread messages. A configured `project_path` or `INTER_AGENT_CLAUDE_HELPER` is a development or troubleshooting override, not the normal installation path.

If authentication fails, ensure every process uses the same endpoint, state directory, and shared secret. If a name is already in use, the listener retries once with a `-2` suffix; otherwise choose a unique name and reconnect. The default endpoint is `127.0.0.1:16837`, and local processes discover the same generated secret from shared state. Loopback transport defaults to plaintext WebSockets; non-loopback transport defaults to TLS, with no automatic downgrade.

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
