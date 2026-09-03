# Changelog

## Unreleased

- Add `/inter-agent doctor [optional context]`, a bounded host-native
  read-only workflow for checking plugin loading, configuration sources,
  helper/runtime resolution, endpoint/TLS details, and (when proven
  non-initializing and non-mutating) Core status. Doctor preserves direct
  command context as symptom/scope data at normal user authority, follows safe
  requests only within the fixed checklist, never executes shell-looking context, treats
  logs/configuration/subprocess output and their embedded commands as untrusted
  and forbidden, redacts secrets, and leaves bootstrap, repair, Monitor, Core
  lifecycle, and messaging operations to explicit user actions.

## 0.2.3

Documentation correction release for the Claude Code plugin and marketplace.

- The plugin and marketplace manifests publish as `0.2.3`.
- Managed bootstrap defaults to the matching `inter-agent--v0.2.3` archive while
  retaining helper source `0.3.0` and Core dependency `0.3.0`.
- Development guidance names the standalone `inter-agent-claude-code` checkout
  and the `inter-agent-claude` helper executable.

## 0.3.0

Prepublication source compatibility alignment for the Claude Code Python helper.

- The helper distribution is `inter-agent-claude-code` `0.3.0` with an exact
  `inter-agent-core==0.3.0` runtime dependency.
- Development resolution pins the accepted Core source revision while built
  artifacts retain registry-only dependency metadata.

## 0.2.2

Claude Code plugin and marketplace release with the current managed helper
source.

- The plugin and marketplace manifests publish as `0.2.2`.
- Managed bootstrap defaults to the tagged standalone
  `inter-agent--v0.2.2` archive, whose helper source is `0.3.0` and whose
  released Core dependency is `0.3.0`.
- The helper remains Git-hosted rather than separately published to PyPI.

## 0.2.1

Stable-source follow-up release for the Claude Code plugin. The plugin version
is `0.2.1`; the Python helper remains `inter-agent-claude-code` `0.2.0`.

- The managed bootstrap default remains pinned to the tagged standalone
  `inter-agent--v0.2.0` archive.
- The plugin and marketplace manifests now publish as `0.2.1`, allowing the
  stable-source fix to ship without retagging the published `0.2.0` release.

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

### Runtime dependency

- Depends on `inter-agent-core` (`0.2.0`) and `websockets` (`16.0`). The
  committed prepublication lock resolves core from the permanent core root
  pinned in `tool.uv.sources`; extension release work removes that source and
  re-locks against the published core package before publication.
- managed bootstrap defaults to the tagged standalone
  `inter-agent-claude-code` `inter-agent--v0.2.0` archive, pinning the helper
  runtime to the released Claude extension source.

### Not published

- no PyPI publication of the helper, no Git tag or release, no official
  Anthropic marketplace submission, and no registry contact occurred for this
  baseline. The helper is distributed only as local/repository build artifacts and
  via this Git-hosted marketplace.