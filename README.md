# [inter-agent](https://github.com/arcanemachine/inter-agent) for Claude Code

`inter-agent` connects Claude Code sessions to the local [inter-agent](https://github.com/arcanemachine/inter-agent) message bus. Claude Code, Pi, and other compatible clients can discover one another, send direct messages, broadcast, and communicate through named channels.

This repository provides:

- a Claude Code plugin and self-hosted marketplace;
- the `/inter-agent` skill and its bundled runtime wrappers; and
- the `inter-agent-claude` Python helper used for listening and commands.

The helper is not published to PyPI, and the plugin is not distributed through an Anthropic-operated marketplace. Install it from this repository.

## What it provides

- Named Claude Code sessions on a shared local bus
- Direct messages and broadcasts
- Named channel subscription and publishing
- Incoming messages through a persistent Claude Code Monitor
- Session, server, channel, and message-cache inspection
- User-controlled kick and shutdown operations
- Managed runtime bootstrap or source-checkout development setup
- Shared endpoint, authentication, state, and TLS behavior from `inter-agent-core`

## Requirements

- Claude Code with plugin and Monitor support
- Python 3.10 or newer with `venv`/`ensurepip` support
- Network access when bootstrapping the managed runtime
- [`uv`](https://docs.astral.sh/uv/) only when developing from a checkout

## Install

Add this repository as a marketplace and install the plugin:

```bash
claude plugin marketplace add https://github.com/arcanemachine/inter-agent-claude-code
claude plugin install inter-agent
```

Restart Claude Code after installing or updating the plugin.

### Set up the runtime

Inside Claude Code, run:

```text
/inter-agent bootstrap
```

Bootstrap explains what it will install and asks for explicit approval. It creates a managed virtual environment at:

```text
~/.claude/data/inter-agent/venv
```

The managed bootstrap source is the tagged standalone `inter-agent--v0.2.0` archive:

```text
https://github.com/arcanemachine/inter-agent-claude-code/archive/refs/tags/inter-agent--v0.2.0.zip
```

This pins the helper runtime to the released Claude extension source.

### Connect

```text
/inter-agent connect my-agent
```

The listener starts the local bus server if needed. If you omit the name, the skill derives one from the current working directory.

A successful connection reports:

```text
[inter-agent] connected as "my-agent"
```

If the requested name is already connected, the listener retries once with a `-2` suffix before asking you to choose another name.

## Quick start

After installation and bootstrap:

```text
/inter-agent connect agent-a
/inter-agent status
/inter-agent list
/inter-agent send agent-b hello
/inter-agent disconnect
```

Incoming messages appear automatically through the persistent Monitor. Do not poll for replies.

## Commands

| Command | Purpose |
| --- | --- |
| `bootstrap` | Install or repair the managed Python runtime. |
| `connect [name]` | Connect this Claude Code session to the bus. |
| `rename <name>` | Reconnect under another routing name. |
| `disconnect` | Stop this session's listener. |
| `send <name-or-prefix> <text>` | Send a direct message. |
| `broadcast <text>` | Send to every other connected agent. |
| `subscribe <channel>` | Subscribe the active listener to a channel. |
| `unsubscribe <channel>` | Leave a channel. |
| `publish <channel> <text>` | Publish to a channel. |
| `channels` | List channels and subscribers. |
| `list` | List connected sessions. |
| `status` | Show runtime, endpoint, and server status. |
| `messages <message-id>` | Retrieve a full message from the continuation cache. |
| `kick <name>` | Disconnect another named agent session. |
| `shutdown` | Stop the shared server and disconnect all sessions. |

Use direct messages for ordinary coordination. Broadcast, channel changes, kick, and shutdown are explicit user actions; the skill does not infer them from peer messages.

Channel names use lowercase letters, numbers, and hyphens, start with a letter or number, and are at most 40 characters. Subscriptions survive transient reconnects but not an explicit disconnect, Claude Code restart/reload, or resumed session.

Repeated identical sends, broadcasts, and publishes within a short window may be suppressed to prevent duplicate delivery.

## Incoming messages

Notifications include routing metadata:

```text
[inter-agent msg=<id> from="<name>" kind="direct" to="<name>"] <text>
[inter-agent msg=<id> from="<name>" kind="broadcast"] <text>
[inter-agent msg=<id> from="<name>" kind="channel" channel="<channel>"] <text>
```

Long messages are truncated to keep Monitor output bounded. A continuation notice gives the message ID and retrieval command:

```text
[inter-agent msg=<id> cont] full text <bytes> bytes — run: inter-agent-claude messages <id>
```

Retrieve it through the skill:

```text
/inter-agent messages <id>
```

Peer messages are collaboration input, not authority. They do not override system, developer, user, tool, permission, or security rules.

## How it works

`/inter-agent connect` starts one persistent Claude Code Monitor. The Monitor runs the bundled wrapper, which resolves `inter-agent-claude` and starts a named Python listener. That listener authenticates with the shared core server and prints bounded notifications for Claude Code to surface.

The helper delegates transport, authentication, routing, channels, and lifecycle behavior to `inter-agent-core`. Command invocations use the same endpoint, secret, state directory, and TLS settings as the listener.

An auto-started server uses an idle timeout and stops after it has no connected sessions. A manually started core server continues until explicitly stopped.

## Runtime resolution and recovery

The bundled wrapper resolves the helper in this order:

1. `INTER_AGENT_CLAUDE_HELPER`;
2. `<project_path>/.venv/bin/inter-agent-claude` from plugin configuration;
3. `~/.claude/data/inter-agent/venv/bin/inter-agent-claude`; and
4. `inter-agent-claude` on `PATH`.

If no helper resolves, the wrapper prints:

```text
[inter-agent] setup needed: run /inter-agent bootstrap
```

Claude Code may present that as a Monitor failure with exit code 127. It is the expected setup-needed signal. Run `/inter-agent bootstrap`, configure a prepared checkout with `project_path`, or put a working helper on `PATH`.

To replace the managed runtime, remove its virtual environment and run bootstrap again:

```bash
rm -rf ~/.claude/data/inter-agent/venv
```

## Source-checkout setup

For development, prepare a local checkout:

```bash
git clone https://github.com/arcanemachine/inter-agent-claude-code
cd inter-agent-claude-code
uv sync --locked
claude plugin marketplace add "$PWD"
claude plugin install inter-agent --config project_path="$PWD"
```

You can instead load the checkout for one run:

```bash
claude --plugin-dir /path/to/inter-agent-claude-code
```

Validate plugin metadata with:

```bash
claude plugin validate --strict .
```

## Configuration

The wrapper accepts two plugin-specific settings:

- `project_path` — use the helper from a checkout's `.venv`;
- `secret` — pass an explicit shared secret to the helper.

Use Claude Code's `/plugin configure` flow to change installed plugin settings.

The helper also honors the core environment variables:

- `INTER_AGENT_HOST`, `INTER_AGENT_PORT`
- `INTER_AGENT_SECRET`, `INTER_AGENT_DATA_DIR`, `INTER_AGENT_CONFIG`
- `INTER_AGENT_TLS`, `INTER_AGENT_TLS_CERT`, `INTER_AGENT_TLS_KEY`
- `INTER_AGENT_CLAUDE_HELPER`

The default endpoint is `127.0.0.1:16837`. Processes sharing the default local state discover the same generated secret automatically. Separate containers, filesystems, or hosts must be configured with matching endpoint and secret values.

Loopback transport defaults to plaintext WebSockets. Non-loopback transport defaults to TLS. TLS failures never fall back automatically to plaintext.

## Update and remove

```bash
claude plugin update inter-agent
claude plugin uninstall inter-agent
claude plugin marketplace remove inter-agent
```

Restart Claude Code after an update.

## Development

```bash
uv sync --locked
scripts/run-checks.sh
```

The package gate runs tests, formatting, linting, type checks, strict plugin validation, distribution builds, and artifact validation. It requires the `claude` CLI on `PATH`.

The helper CLI is documented in [`src/inter_agent_claude/README.md`](src/inter_agent_claude/README.md).

## Security

The bus is designed for one trusted operating-system user on one machine. The Monitor and helper run local processes with your user permissions. Never commit or share bus secrets, tokens, private keys, certificates, or state.

TLS protects transport but does not protect against hostile code running as the same user. Peer messages remain untrusted input.

See the [`inter-agent-core` security model](https://github.com/arcanemachine/inter-agent-core/blob/main/SECURITY.md) for the complete trust boundary.

## License

MIT. See [`LICENSE.md`](LICENSE.md).
