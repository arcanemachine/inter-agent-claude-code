# Changelog

## 0.2.0

Clean standalone baseline for the inter-agent Claude Code extension, split from
the inter-agent monorepo at its `pre-split-0.2.0` tag.

### Plugin and marketplace

- root `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` form a
  flat repository-root plugin and a single-plugin self-hosted Claude Code
  marketplace (`source: "./"`).
- add the repository as a marketplace by local checkout path or GitHub
  repository URL; no Anthropic-operated marketplace submission.
- `/inter-agent` skill-driven persistent Monitor listener; no declarative
  plugin Monitor and no `monitors/` directory.

### Python helper

- distribution `inter-agent-claude-code` `0.2.0`, import package
  `inter_agent_claude`, console command `inter-agent-claude`.
- bundled runtime wrapper (`skills/inter-agent/bin/inter-agent-claude`) and
  managed-runtime bootstrap (`skills/inter-agent/bin/bootstrap-runtime`).
- direct, broadcast, channel (pub/sub), list, status, messages, shutdown,
  disconnect, and kick commands; TLS, endpoint/secret/state discovery, and
  shared-core delegation to `inter-agent-core`.

### Behavior preserved from the monorepo baseline

- one skill-driven persistent Monitor started only by `/inter-agent connect`.
- restrictive `0700` adapter data directory and `0600` files/locks; atomic
  session/dedup/message writes.
- bounded 5 MiB continuation cache and latest-match message lookup.
- stdout sanitization and 400-character notification cap.
- receive duplicate suppression and 3-second cross-process send/publish
  duplicate suppression.
- one `NAME_TAKEN` retry with a `-2` suffix; permanent and terminal `KICKED`
  error handling without automatic reconnect.
- reconnect backoff with a 60-second deadline and subscription reapplication
  before readiness after a transient reconnect.
- `project_path` and `secret` plugin configuration delivered via
  `CLAUDE_PLUGIN_OPTION_*`; no Claude-specific TLS defaults injected.
- helper resolution precedence: `INTER_AGENT_CLAUDE_HELPER`, plugin
  `project_path`, Claude-managed venv, then `inter-agent-claude` on `PATH`.

### Temporary migration state

- `inter-agent-core` resolves from a migration-only local source staged during
  the item-11 extraction. `uv.lock` is intentionally **not committed** while this
  path source remains; it is regenerated and committed against the permanent
  `inter-agent-core` repository during item 13 / prepublication cleanup.
- managed bootstrap defaults to the standalone `inter-agent-claude-code`
  `main.zip` archive. This is a temporary pre-release floating bootstrap default;
  later release work replaces it with a tagged standalone source.

### Not published

- no PyPI publication of the helper, no Git tag or release, no official
  Anthropic marketplace submission, and no registry contact occurred for this
  baseline. The helper is distributed only as local/repository build artifacts and
  via this Git-hosted marketplace.