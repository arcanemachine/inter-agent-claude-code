from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLAUDE_PLUGIN_DIR = ROOT
PLUGIN_MANIFEST = CLAUDE_PLUGIN_DIR / ".claude-plugin" / "plugin.json"
MARKETPLACE_MANIFEST = ROOT / ".claude-plugin" / "marketplace.json"
SKILL_DIR = ROOT / "skills" / "inter-agent"
MONITORS_DIR = ROOT / "monitors"


def test_claude_marketplace_manifest_points_to_claude_plugin() -> None:
    """The root marketplace metadata must install the Claude plugin subdirectory."""
    marketplace = json.loads(MARKETPLACE_MANIFEST.read_text(encoding="utf-8"))
    plugin_manifest = json.loads(PLUGIN_MANIFEST.read_text(encoding="utf-8"))

    assert marketplace["$schema"] == "https://json.schemastore.org/claude-code-marketplace.json"
    assert marketplace["name"] == "inter-agent"
    assert marketplace["version"] == plugin_manifest["version"]
    assert marketplace["owner"]["name"]
    assert marketplace["owner"]["email"]

    plugins = marketplace["plugins"]
    assert len(plugins) == 1
    plugin = plugins[0]
    assert plugin["name"] == plugin_manifest["name"]
    assert plugin["version"] == plugin_manifest["version"]
    assert plugin_manifest["author"]["name"] == plugin["author"]["name"]
    assert plugin_manifest["author"]["email"] == plugin["author"]["email"]
    assert plugin["category"] == "productivity"

    user_config = plugin_manifest["userConfig"]
    project_path = user_config["project_path"]
    assert project_path["type"] == "string"
    assert project_path["default"] == ""
    assert ".venv/bin/inter-agent-claude" in project_path["description"]
    secret = user_config["secret"]
    assert secret["type"] == "string"
    assert secret["default"] == ""
    assert "INTER_AGENT_SECRET" in secret["description"]

    source = plugin["source"]
    assert source == "./"
    assert not source.startswith("/")
    assert (ROOT / source).resolve() == CLAUDE_PLUGIN_DIR.resolve()
    assert ((ROOT / source) / ".claude-plugin" / "plugin.json").is_file()
    assert ((ROOT / source) / ".claude-plugin" / "marketplace.json").is_file()
    assert ((ROOT / source) / "skills" / "inter-agent" / "SKILL.md").is_file()


def test_claude_plugin_manifest_declares_no_declarative_monitors() -> None:
    """The plugin must not declare an `on-skill-invoke` Monitor.

    A plugin-declared Monitor would race the skill-driven
    `inter-agent-claude listen --name <name>` Monitor for the same per-session
    flock and emit a confusing "another listener is already starting or
    running" line (and, because the declarative command carries no `--name`,
    could connect under the wrong cwd-derived name if it won the race).
    Connect is driven solely by the `/inter-agent` skill, which starts a
    single Monitor with the user's chosen routing name.
    """
    manifest = json.loads(PLUGIN_MANIFEST.read_text(encoding="utf-8"))
    assert "monitors" not in manifest, (
        "plugin.json must not declare a monitors entry; the listener is "
        "started on demand by the /inter-agent skill with the user's name"
    )


def test_claude_plugin_has_no_monitors_directory() -> None:
    """No plugin-declared Monitor assets should ship with the repository."""
    assert not MONITORS_DIR.exists(), (
        "monitors/ must not exist; a plugin-declared Monitor races the "
        "skill-driven listener and causes duplicate launches"
    )


def test_claude_plugin_and_marketplace_versions_are_synchronized() -> None:
    """Plugin and marketplace manifest versions must move together."""
    plugin_manifest = json.loads(PLUGIN_MANIFEST.read_text(encoding="utf-8"))
    marketplace = json.loads(MARKETPLACE_MANIFEST.read_text(encoding="utf-8"))
    assert plugin_manifest["version"] == marketplace["version"]
    assert marketplace["plugins"][0]["version"] == plugin_manifest["version"]


def test_claude_setup_source_and_documented_helper_version_are_mapped() -> None:
    plugin_manifest = json.loads(PLUGIN_MANIFEST.read_text(encoding="utf-8"))
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    setup_script = (SKILL_DIR / "bin" / "bootstrap-runtime").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    setup = (SKILL_DIR / "setup.md").read_text(encoding="utf-8")

    plugin_version = plugin_manifest["version"]
    helper_version = project["project"]["version"]
    assert f"inter-agent--v{plugin_version}.zip" in setup_script
    assert f"helper `inter-agent-claude` `{helper_version}`" in readme
    assert f"helper source `inter-agent-claude-code` `{helper_version}`" in setup
    core_version = project["project"]["dependencies"][0].split("==", 1)[1]
    assert f"`inter-agent-core=={core_version}`" in setup
    assert "INTER_AGENT_CLAUDE_BOOTSTRAP_SOURCE" not in setup_script
    assert "INTER_AGENT_CLAUDE_BOOTSTRAP_PYTHON" not in setup_script

    source_match = re.search(r"DEFAULT_SOURCE=.*inter-agent--v([0-9.]+)\.zip", setup_script)
    assert source_match is not None
    assert source_match.group(1) == plugin_version


def test_claude_plugin_has_no_nested_plugin_directory_or_parent_traversal() -> None:
    """The marketplace source must resolve to the flat repository root, not a
    nested `integrations/claude-code` plugin subdirectory or a parent path."""
    marketplace = json.loads(MARKETPLACE_MANIFEST.read_text(encoding="utf-8"))
    source = marketplace["plugins"][0]["source"]
    assert source == "./"
    assert ".." not in source.split("/")
    assert "integrations/claude-code" not in source
    resolved = (ROOT / source).resolve()
    assert resolved == ROOT.resolve()
    assert (resolved / ".claude-plugin" / "plugin.json").is_file()
    assert not (ROOT / "integrations" / "claude-code").exists()
