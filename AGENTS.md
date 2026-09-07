# Claude Code extension guidance

## Release tags

Use plain annotated semantic-version tags: `vMAJOR.MINOR.PATCH` (for example,
`v0.2.4`). The older `inter-agent--v...` tags are historical and must not be
used for new releases.

Keep the plugin and marketplace versions, managed setup source URL, setup and
README release references, changelog, and version-sensitive tests synchronized.
Push the child commit and tag before updating the ecosystem submodule pin. The
user performs all pushes and publication.
