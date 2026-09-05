# inter-agent Claude helper

The `inter_agent_claude` package is the Python helper for the
`inter-agent` Claude Code plugin. It is installed through the
`inter-agent-claude` console command and driven by the
[`/inter-agent` skill](../../README.md) (see the root `README.md` for plugin and
marketplace installation).

The packaged wrapper owns managed setup through `/inter-agent setup`; setup is
not a helper subcommand. It uses `python -m venv` and the environment's
`python -m pip` only after explicit approval. The wrapper resolves explicit and
project overrides before the managed venv, and setup never modifies those
overrides.

## Commands

Run Claude adapter commands through the installed package entry point:

- `inter-agent-claude listen --name <name> [--label <label>]`
- `inter-agent-claude send <to> <text>`
- `inter-agent-claude broadcast <text>`
- `inter-agent-claude subscribe <channel>`
- `inter-agent-claude unsubscribe <channel>`
- `inter-agent-claude publish <channel> <text>`
- `inter-agent-claude channels [--json]`
- `inter-agent-claude list [--json]`
- `inter-agent-claude status [--json]`
- `inter-agent-claude messages <msg_id> [--json]`
- `inter-agent-claude shutdown`
- `inter-agent-claude disconnect`
- `inter-agent-claude kick <name>`

`send`, `broadcast`, `subscribe`, `unsubscribe`, and `publish` require an active
listener for the current Claude Code session. The adapter uses that listener's
connected routing name as the sender name. Use `send` for normal replies and
targeted coordination. Use `broadcast` only when the user explicitly asks to
message everyone or the information is genuinely for every connected session.

`send` and `broadcast` suppress identical repeated invocations within a short
window (a few seconds) so that an agent loop re-firing the same command does not
produce duplicate deliveries. A later re-send of the same text after the window
passes is delivered normally.

`messages <msg_id>` reads the full text of a truncated inbound message from the
bounded local continuation cache by message ID, so the agent does not have to
grep or tail the log file directly. The cache defaults to 5 MiB and can be
adjusted for manual testing with `INTER_AGENT_CLAUDE_MESSAGES_LOG_MAX_BYTES`.

## Channels (pub/sub)

`subscribe` and `unsubscribe` operate on the matched live listener for the
current session, not on a new connection. They are delivered through a private
local Unix-domain control socket and print the raw protocol acknowledgment JSON
(`subscribe_ok` / `unsubscribe_ok`) on success. Protocol errors print an
adapter-prefixed diagnostic to stderr and return a non-zero exit code. A missing,
stale, or reconnecting listener fails cleanly without a traceback.

`publish <channel> <text>` publishes to a channel. Claude publish requires the
active listener identity and ignores any caller-supplied sender; it applies
short-window duplicate suppression keyed by sender, channel, and text so an agent
loop re-firing the same command does not produce duplicate deliveries. Claude
publish success is silent (stdout stays empty); protocol errors such as
`UNKNOWN_CHANNEL` are reported on stderr with a non-zero exit code.

`channels [--json]` lists channels and their subscribers as the raw
`channels_ok` protocol JSON.

Inbound channel messages are rendered distinctly as
`kind="channel" channel="<channel>"`; direct and broadcast notifications keep
their existing `kind="direct"` and `kind="broadcast"` output. Channel messages
retain truncation, continuation lookup, receive deduplication, and sanitization
behavior.

Subscriptions are retained across transient listener reconnects: the listener
re-applies the desired subscription set after reconnecting and before reporting
readiness. Subscriptions are not persisted across an explicit listener stop or
process restart; there are no automatic or default subscriptions.

## Server auto-start and idle timeout

The `listen` command auto-starts the server if it is not already running.
Listener-started servers use an explicit 300-second idle timeout and shut down
after that period with no connected sessions. You do not need to start the
server manually before using the listener; if you do start `inter-agent-server`
manually, it runs until explicit shutdown unless you pass
`--idle-timeout <seconds>`.

## Example workflow

1. Connect two Claude Code sessions using the Monitor listener:
   ```
   /inter-agent connect agent-a
   ```

2. Send a direct message to a routing name:
   ```
   /inter-agent send agent-b "run tests"
   ```

3. Broadcast only when every connected session needs the message:
   ```
   /inter-agent broadcast "build is green for everyone"
   ```

4. Inspect sessions and server state:
   ```
   /inter-agent list
   /inter-agent status
   ```

5. Disconnect from the bus:
   ```
   /inter-agent disconnect
   ```

6. Stop the local server:
   ```
   /inter-agent shutdown
   ```

## Output and failures

Helper command output is JSON-oriented. Stdout is reserved for protocol or
status payloads. Stderr is reserved for local diagnostics. The wrapper has one
preflight exception: when no helper exists or a selected runtime is unusable,
it emits exactly one bounded setup diagnosis on stdout and exits `3` or `4` so a
Claude Code Monitor can display it. Successful helper output remains unchanged;
ordinary diagnostics after the helper starts remain on stderr.

`status` prints a JSON status object with `state`, `host`, `port`,
`server_reachable`, `message`, `core_list_supported`, `adapter_list_exposed`,
`connected`, `connected_name`, `data_dir`, and `data_dir_source` fields when
available. `connected` is true when a live listener is registered for the
current Claude Code session; `connected_name` is the routing name that listener
uses (or null when not connected).

The current status implementation can initialize or modify adapter state while
resolving these fields, including creating/chmodding directories, locks, or a
fallback token. It is not a strictly read-only statusline API. Adapter files
under `<data_dir>/claude-sessions/`, including their filenames and JSON fields,
are internal implementation details and are not stable external interfaces.

## Permanent errors

The listener exits without reconnecting on permanent errors: `AUTH_FAILED`,
`BAD_ROLE`, `BAD_NAME`, `BAD_SESSION`, `SESSION_TAKEN`, `BAD_LABEL`,
`TOO_MANY_CONNECTIONS`. On `NAME_TAKEN`, the Claude listener retries once with a
`-2` suffix and exits only if that retry is also taken. Transient errors trigger
reconnection with bounded backoff. A `KICKED` error is terminal: the listener
stops reconnecting for its process and the removed name is immediately free for
an explicit later reconnect.