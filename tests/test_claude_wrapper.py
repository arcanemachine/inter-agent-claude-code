from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL_BIN = ROOT / "skills" / "inter-agent" / "bin"
WRAPPER = SKILL_BIN / "inter-agent-claude"
SETUP = SKILL_BIN / "bootstrap-runtime"

#: Each entry maps a presence field name to the INTER_AGENT_* variable the
#: fake helper inspects. The helper emits only fixed boolean eq/presence
#: fields; no raw or hash-derived values are ever written to stdout.
PRESENCE_FIELDS = [
    ("DATA_DIR", "INTER_AGENT_DATA_DIR"),
    ("TLS", "INTER_AGENT_TLS"),
    ("TLS_CERT", "INTER_AGENT_TLS_CERT"),
    ("TLS_KEY", "INTER_AGENT_TLS_KEY"),
    ("SECRET", "INTER_AGENT_SECRET"),
]


def make_presence_helper(path: Path, expected: dict[str, str]) -> None:
    """Write a helper that emits fixed boolean equality/presence fields only."""
    lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        'emit() { local name="$1" actual="$2" expected="$3"; '
        'if [[ "$actual" == "$expected" ]]; then printf "%s_eq=true\\n" "$name"; '
        'else printf "%s_eq=false\\n" "$name"; fi; '
        'if [[ -n "$actual" ]]; then printf "%s_present=true\\n" "$name"; '
        'else printf "%s_present=false\\n" "$name"; fi; }',
    ]
    for name, var in PRESENCE_FIELDS:
        lines.append(f'emit {name} "${{{var}:-}}" {shlex.quote(expected.get(name, ""))}')
    lines.append("printf 'ARGS_BEGIN\\n'")
    lines.append('printf "%s\\n" "$@"')
    lines.append("printf 'ARGS_END\\n'")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    path.chmod(0o755)


def _parse_presence(stdout: str) -> dict[str, str]:
    summary: dict[str, str] = {}
    for line in stdout.splitlines():
        if line.startswith("ARGS_BEGIN") or line.startswith("ARGS_END"):
            continue
        if "=" in line:
            key, _, value = line.partition("=")
            summary[key] = value
    return summary


def _parse_args(stdout: str) -> list[str]:
    lines = stdout.splitlines()
    start = lines.index("ARGS_BEGIN") + 1
    end = lines.index("ARGS_END")
    return lines[start:end]


def make_helper(path: Path, label: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "#!/usr/bin/env bash\n" "set -euo pipefail\n" f"printf '{label}:%s\\n' \"$*\"\n",
        encoding="utf-8",
    )
    path.chmod(0o755)


def make_broken_interpreter_helper(path: Path) -> None:
    """An executable helper whose shebang interpreter does not exist."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/no/such/interpreter\necho should-not-run\n", encoding="utf-8")
    path.chmod(0o755)


def run_wrapper(
    tmp_path: Path, *args: str, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    runtime_env = {
        "HOME": str(tmp_path / "home"),
        "PATH": "/usr/bin:/bin",
    }
    if env:
        runtime_env.update(env)
    return subprocess.run(
        ["bash", str(WRAPPER), *args],
        env=runtime_env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_claude_wrapper_help_is_available_without_runtime(tmp_path: Path) -> None:
    result = run_wrapper(tmp_path, "--help")

    assert result.returncode == 0
    assert "setup --yes" in result.stdout
    assert "bootstrap" not in result.stdout
    assert result.stderr == ""


def test_claude_wrapper_setup_help_is_available_without_runtime(tmp_path: Path) -> None:
    result = run_wrapper(tmp_path, "setup", "--help")

    assert result.returncode == 0
    assert "Usage: inter-agent-claude setup --yes" in result.stdout
    assert "--source" in result.stdout
    assert "bootstrap" not in result.stdout.lower()
    assert result.stderr == ""


def test_claude_wrapper_env_helper_override_wins(tmp_path: Path) -> None:
    env_helper = tmp_path / "env" / "inter-agent-claude"
    config_helper = tmp_path / "checkout" / ".venv" / "bin" / "inter-agent-claude"
    make_helper(env_helper, "env")
    make_helper(config_helper, "config")

    result = run_wrapper(
        tmp_path,
        "status",
        "--json",
        env={
            "INTER_AGENT_CLAUDE_HELPER": str(env_helper),
            "CLAUDE_PLUGIN_OPTION_PROJECT_PATH": str(tmp_path / "checkout"),
        },
    )

    assert result.returncode == 0
    assert result.stdout == "env:status --json\n"


def test_claude_wrapper_uses_plugin_project_path(tmp_path: Path) -> None:
    project_path = tmp_path / "checkout"
    helper = project_path / ".venv" / "bin" / "inter-agent-claude"
    make_helper(helper, "config")

    result = run_wrapper(
        tmp_path,
        "list",
        env={"CLAUDE_PLUGIN_OPTION_PROJECT_PATH": str(project_path)},
    )

    assert result.returncode == 0
    assert result.stdout == "config:list\n"


def test_claude_wrapper_uses_managed_venv_before_path(tmp_path: Path) -> None:
    managed = tmp_path / "home" / ".claude" / "data" / "inter-agent" / "venv"
    managed_helper = managed / "bin" / "inter-agent-claude"
    path_helper = tmp_path / "path" / "inter-agent-claude"
    make_helper(managed_helper, "managed")
    make_helper(path_helper, "path")

    result = run_wrapper(
        tmp_path,
        "status",
        env={"PATH": f"{path_helper.parent}{os.pathsep}/usr/bin:/bin"},
    )

    assert result.returncode == 0
    assert result.stdout == "managed:status\n"


def test_claude_wrapper_reports_missing_runtime_on_stdout(tmp_path: Path) -> None:
    result = run_wrapper(tmp_path, "status")

    assert result.returncode == 3
    assert result.stderr == ""
    assert result.stdout.count("\n") == 1
    assert "/inter-agent setup" in result.stdout
    assert "README.md#recovery-and-configuration" in result.stdout
    assert "bootstrap" not in result.stdout.lower()
    assert len(result.stdout) <= 512


def test_claude_wrapper_bootstrap_is_not_a_compatibility_alias(tmp_path: Path) -> None:
    result = run_wrapper(tmp_path, "bootstrap")

    assert result.returncode == 3
    assert "/inter-agent setup" in result.stdout
    assert "bootstrap" not in result.stdout.lower()
    assert result.stderr == ""


def test_claude_setup_requires_yes(tmp_path: Path) -> None:
    result = run_wrapper(tmp_path, "setup")

    assert result.returncode == 2
    assert result.stdout == ""
    assert "setup approval required" in result.stderr
    assert "rerun setup with --yes" in result.stderr
    assert not (tmp_path / "home" / ".claude" / "data" / "inter-agent" / "venv").exists()
    assert "bootstrap" not in result.stderr.lower()


def test_claude_setup_source_uses_tagged_archive_and_new_overrides() -> None:
    script = SETUP.read_text(encoding="utf-8")

    expected_source = (
        "https://github.com/arcanemachine/inter-agent-claude-code/archive/refs/tags/"
        "inter-agent--v0.2.3.zip"
    )
    assert expected_source in script
    assert "INTER_AGENT_CLAUDE_SETUP_SOURCE" in script
    assert "INTER_AGENT_CLAUDE_SETUP_PYTHON" in script
    assert "INTER_AGENT_CLAUDE_BOOTSTRAP_SOURCE" not in script
    assert "INTER_AGENT_CLAUDE_BOOTSTRAP_PYTHON" not in script
    assert "--source" in script
    assert "--yes" in script
    assert "Python 3.10+ not found" in script
    assert "-m venv" in script
    assert "-m pip" in script


def test_claude_wrapper_passes_plugin_secret_to_helper(tmp_path: Path) -> None:
    project_path = tmp_path / "checkout"
    helper = project_path / ".venv" / "bin" / "inter-agent-claude"
    helper.parent.mkdir(parents=True, exist_ok=True)
    helper.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "printf 'secret:%s\\n' \"${INTER_AGENT_SECRET:-}\"\n",
        encoding="utf-8",
    )
    helper.chmod(0o755)

    result = run_wrapper(
        tmp_path,
        "status",
        env={
            "CLAUDE_PLUGIN_OPTION_PROJECT_PATH": str(project_path),
            "CLAUDE_PLUGIN_OPTION_SECRET": "plugin-secret",
        },
    )

    assert result.returncode == 0
    assert result.stdout == "secret:plugin-secret\n"


def test_claude_wrapper_forwards_channels_argument_unchanged(tmp_path: Path) -> None:
    project_path = tmp_path / "checkout"
    helper = project_path / ".venv" / "bin" / "inter-agent-claude"
    helper.parent.mkdir(parents=True, exist_ok=True)
    helper.write_text(
        "#!/usr/bin/env bash\nset -euo pipefail\nprintf '%s\\n' \"$@\"\n",
        encoding="utf-8",
    )
    helper.chmod(0o755)

    result = run_wrapper(
        tmp_path,
        "channels",
        env={"CLAUDE_PLUGIN_OPTION_PROJECT_PATH": str(project_path)},
    )

    assert result.returncode == 0
    assert result.stdout.splitlines() == ["channels"]
    assert result.stderr == ""


def test_claude_wrapper_forwards_publish_arguments_unchanged(tmp_path: Path) -> None:
    project_path = tmp_path / "checkout"
    helper = project_path / ".venv" / "bin" / "inter-agent-claude"
    helper.parent.mkdir(parents=True, exist_ok=True)
    helper.write_text(
        "#!/usr/bin/env bash\nset -euo pipefail\nprintf '%s\\n' \"$@\"\n",
        encoding="utf-8",
    )
    helper.chmod(0o755)

    result = run_wrapper(
        tmp_path,
        "publish",
        "updates",
        "build is green",
        env={"CLAUDE_PLUGIN_OPTION_PROJECT_PATH": str(project_path)},
    )

    assert result.returncode == 0
    assert result.stdout.splitlines() == ["publish", "updates", "build is green"]
    assert result.stderr == ""


def test_claude_wrapper_env_helper_not_executable_fails_bounded(tmp_path: Path) -> None:
    helper = tmp_path / "env" / "inter-agent-claude"
    helper.parent.mkdir(parents=True, exist_ok=True)
    helper.write_text("#!/usr/bin/env bash\necho nope\n", encoding="utf-8")

    result = run_wrapper(
        tmp_path,
        "status",
        env={"INTER_AGENT_CLAUDE_HELPER": str(helper)},
    )

    assert result.returncode == 4
    assert result.stderr == ""
    assert result.stdout.count("\n") == 1
    assert "runtime unavailable (explicit)" in result.stdout
    assert "INTER_AGENT_CLAUDE_HELPER" in result.stdout
    assert "does not modify overrides" in result.stdout
    assert "README.md#recovery-and-configuration" in result.stdout


def test_claude_wrapper_env_helper_broken_interpreter_fails_bounded(tmp_path: Path) -> None:
    helper = tmp_path / "env" / "inter-agent-claude"
    make_broken_interpreter_helper(helper)

    result = run_wrapper(
        tmp_path,
        "status",
        env={"INTER_AGENT_CLAUDE_HELPER": str(helper)},
    )

    assert result.returncode == 4
    assert result.stderr == ""
    assert "INTER_AGENT_CLAUDE_HELPER interpreter not executable" in result.stdout
    assert "/no/such/interpreter" in result.stdout
    assert "README.md#recovery-and-configuration" in result.stdout
    assert "cannot execute" not in result.stdout


def test_claude_wrapper_project_path_helper_not_executable_fails_bounded(
    tmp_path: Path,
) -> None:
    project_path = tmp_path / "checkout"
    helper = project_path / ".venv" / "bin" / "inter-agent-claude"
    helper.parent.mkdir(parents=True, exist_ok=True)
    helper.write_text("#!/usr/bin/env bash\necho nope\n", encoding="utf-8")

    result = run_wrapper(
        tmp_path,
        "status",
        env={"CLAUDE_PLUGIN_OPTION_PROJECT_PATH": str(project_path)},
    )

    assert result.returncode == 4
    assert result.stderr == ""
    assert "runtime unavailable (project)" in result.stdout
    assert "configured project_path" in result.stdout
    assert "does not modify overrides" in result.stdout


def test_claude_wrapper_managed_missing_helper_is_broken_runtime(tmp_path: Path) -> None:
    managed = tmp_path / "home" / ".claude" / "data" / "inter-agent" / "venv"
    (managed / "bin").mkdir(parents=True)
    (managed / "pyvenv.cfg").write_text("home = /usr/bin\n", encoding="utf-8")

    result = run_wrapper(tmp_path, "status")

    assert result.returncode == 4
    assert result.stderr == ""
    assert "runtime unavailable (managed)" in result.stdout
    assert "/inter-agent setup" in result.stdout


def test_claude_wrapper_managed_helper_broken_interpreter_fails_bounded(
    tmp_path: Path,
) -> None:
    managed = tmp_path / "home" / ".claude" / "data" / "inter-agent" / "venv"
    make_broken_interpreter_helper(managed / "bin" / "inter-agent-claude")

    result = run_wrapper(tmp_path, "status")

    assert result.returncode == 4
    assert result.stderr == ""
    assert "managed venv interpreter not executable" in result.stdout
    assert "/no/such/interpreter" in result.stdout
    assert "/inter-agent setup" in result.stdout


def test_claude_wrapper_uses_path_helper_when_no_managed_or_project(tmp_path: Path) -> None:
    path_helper = tmp_path / "path" / "inter-agent-claude"
    make_helper(path_helper, "path")

    result = run_wrapper(
        tmp_path,
        "status",
        env={"PATH": f"{path_helper.parent}{os.pathsep}/usr/bin:/bin"},
    )

    assert result.returncode == 0
    assert result.stdout == "path:status\n"


def test_claude_wrapper_path_helper_broken_interpreter_fails_bounded(
    tmp_path: Path,
) -> None:
    path_helper = tmp_path / "path" / "inter-agent-claude"
    make_broken_interpreter_helper(path_helper)

    result = run_wrapper(
        tmp_path,
        "status",
        env={"PATH": f"{path_helper.parent}{os.pathsep}/usr/bin:/bin"},
    )

    assert result.returncode == 4
    assert result.stderr == ""
    assert "runtime unavailable (path)" in result.stdout
    assert "PATH interpreter not executable" in result.stdout
    assert "/inter-agent setup" in result.stdout


def test_claude_wrapper_skips_path_helper_equal_to_self(tmp_path: Path) -> None:
    result = run_wrapper(
        tmp_path,
        "status",
        env={"PATH": f"{SKILL_BIN}{os.pathsep}/usr/bin:/bin"},
    )

    assert result.returncode == 3
    assert result.stderr == ""
    assert "/inter-agent setup" in result.stdout


def test_claude_wrapper_bounds_adversarial_helper_path(tmp_path: Path) -> None:
    long_path = "/" + ("segment/" * 600) + "inter-agent-claude"

    result = run_wrapper(
        tmp_path,
        "status",
        env={"INTER_AGENT_CLAUDE_HELPER": long_path},
    )

    assert result.returncode == 4
    assert result.stderr == ""
    assert len(result.stdout) <= 512
    assert "runtime unavailable (explicit)" in result.stdout
    assert "does not modify overrides" in result.stdout
    assert "README.md#recovery-and-configuration" in result.stdout


def test_claude_wrapper_forwards_tls_data_and_secret_to_helper_unchanged(
    tmp_path: Path,
) -> None:
    project_path = tmp_path / "checkout"
    helper = project_path / ".venv" / "bin" / "inter-agent-claude"
    data_dir = str(tmp_path / "state")
    tls_cert = str(tmp_path / "certs" / "tls-cert.pem")
    tls_key = str(tmp_path / "certs" / "tls-key.pem")
    secret_value = "claude-wrapper-tls-test-secret"
    expected = {
        "DATA_DIR": data_dir,
        "TLS": "true",
        "TLS_CERT": tls_cert,
        "TLS_KEY": tls_key,
        "SECRET": secret_value,
    }
    make_presence_helper(helper, expected)

    result = run_wrapper(
        tmp_path,
        "status",
        "--json",
        env={
            "CLAUDE_PLUGIN_OPTION_PROJECT_PATH": str(project_path),
            "CLAUDE_PLUGIN_OPTION_SECRET": secret_value,
            "INTER_AGENT_DATA_DIR": data_dir,
            "INTER_AGENT_TLS": "true",
            "INTER_AGENT_TLS_CERT": tls_cert,
            "INTER_AGENT_TLS_KEY": tls_key,
        },
    )

    assert result.returncode == 0
    summary = _parse_presence(result.stdout)
    for name in ("DATA_DIR", "TLS", "TLS_CERT", "TLS_KEY", "SECRET"):
        assert summary[f"{name}_eq"] == "true", name
        assert summary[f"{name}_present"] == "true", name
    assert _parse_args(result.stdout) == ["status", "--json"]

    for stream in (result.stdout, result.stderr):
        assert secret_value not in stream
        assert tls_cert not in stream
        assert tls_key not in stream
        assert data_dir not in stream
    assert secret_value not in result.args


def test_claude_wrapper_adds_no_claude_specific_tls_defaults(tmp_path: Path) -> None:
    project_path = tmp_path / "checkout"
    helper = project_path / ".venv" / "bin" / "inter-agent-claude"
    make_presence_helper(
        helper,
        {"TLS": "true", "TLS_CERT": "/x", "TLS_KEY": "/y", "SECRET": "s"},
    )

    result = run_wrapper(
        tmp_path,
        "channels",
        env={"CLAUDE_PLUGIN_OPTION_PROJECT_PATH": str(project_path)},
    )

    assert result.returncode == 0
    summary = _parse_presence(result.stdout)
    for name in ("TLS", "TLS_CERT", "TLS_KEY", "SECRET"):
        assert summary[f"{name}_present"] == "false", name
    assert _parse_args(result.stdout) == ["channels"]


def test_claude_wrapper_bin_assets_are_executable() -> None:
    for asset in (WRAPPER, SETUP):
        assert asset.is_file()
        assert asset.stat().st_mode & 0o111, f"{asset} is not executable"


def _make_fake_python(path: Path, log: Path) -> None:
    path.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        'printf \'%s\\n\' "$*" >> "$FAKE_PYTHON_LOG"\n'
        "if [[ \"$1\" == '-m' && \"$2\" == 'venv' ]]; then\n"
        '  if [[ "${FAKE_FAIL_VENV:-}" == 1 ]]; then exit 1; fi\n'
        '  target="${@: -1}"\n'
        '  mkdir -p "$target/bin"\n'
        "  printf 'home = /usr/bin\\n' > \"$target/pyvenv.cfg\"\n"
        '  cp "$0" "$target/bin/python"\n'
        '  chmod +x "$target/bin/python"\n'
        "elif [[ \"$1\" == '-m' && \"$2\" == 'pip' && \"$3\" == '--version' ]]; then\n"
        '  if [[ "${FAKE_FAIL_PIP:-}" == 1 ]]; then exit 1; fi\n'
        "  printf 'pip 1.0\\n'\n"
        "elif [[ \"$1\" == '-m' && \"$2\" == 'pip' && \"$3\" == 'install' ]]; then\n"
        '  if [[ "${FAKE_FAIL_INSTALL:-}" == 1 ]]; then exit 1; fi\n'
        '  if [[ "${FAKE_SKIP_HELPER:-}" == 1 ]]; then exit 0; fi\n'
        '  root="$(cd "$(dirname "$0")/.." && pwd)"\n'
        '  if [[ "${FAKE_BROKEN_HELPER:-}" == 1 ]]; then\n'
        "    printf '#!/no/such/interpreter\\n' > \"$root/bin/inter-agent-claude\"\n"
        "  else\n"
        "    printf '#!/bin/sh\\nprintf setup-helper\\n' > \"$root/bin/inter-agent-claude\"\n"
        "  fi\n"
        '  chmod +x "$root/bin/inter-agent-claude"\n'
        "fi\n",
        encoding="utf-8",
    )
    path.chmod(0o755)
    log.touch()


def run_setup(
    tmp_path: Path,
    venv: Path,
    *,
    source: str | None = None,
    python: Path | None = None,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    fake_python = fake_bin / "python3"
    log = tmp_path / "python.log"
    _make_fake_python(fake_python, log)
    command = [
        "bash",
        str(SETUP),
        "--yes",
        "--venv",
        str(venv),
        "--source",
        source or str(tmp_path / "source.zip"),
    ]
    if python is not None:
        command.extend(("--python", str(python)))
    env = {
        "HOME": str(tmp_path / "home"),
        "PATH": f"{fake_bin}:/usr/bin:/bin",
        "FAKE_PYTHON_LOG": str(log),
    }
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        command,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_claude_setup_does_not_print_configured_source(tmp_path: Path) -> None:
    secret_source = "https://user:source-secret@example.invalid/inter-agent.zip"
    result = run_setup(tmp_path, tmp_path / "managed" / "venv", source=secret_source)

    assert result.returncode == 0, result.stderr
    assert "configured source" in result.stdout
    assert secret_source not in result.stdout
    assert secret_source not in result.stderr


def test_claude_setup_rejects_invalid_explicit_python(tmp_path: Path) -> None:
    bad_python = tmp_path / "bad-python"
    bad_python.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    bad_python.chmod(0o755)

    result = run_setup(tmp_path, tmp_path / "managed" / "venv", python=bad_python)

    assert result.returncode == 2
    assert "configured setup Python is not a usable" in result.stderr
    assert not (tmp_path / "managed" / "venv").exists()


def test_claude_setup_reports_venv_creation_failure(tmp_path: Path) -> None:
    result = run_setup(
        tmp_path,
        tmp_path / "managed" / "venv",
        extra_env={"FAKE_FAIL_VENV": "1"},
    )

    assert result.returncode == 1
    assert "could not create or repair venv" in result.stderr


def test_claude_setup_reports_pip_failure(tmp_path: Path) -> None:
    result = run_setup(
        tmp_path,
        tmp_path / "managed" / "venv",
        extra_env={"FAKE_FAIL_PIP": "1"},
    )

    assert result.returncode == 1
    assert "venv pip is unavailable" in result.stderr


def test_claude_setup_reports_install_failure(tmp_path: Path) -> None:
    result = run_setup(
        tmp_path,
        tmp_path / "managed" / "venv",
        extra_env={"FAKE_FAIL_INSTALL": "1"},
    )

    assert result.returncode == 1
    assert "runtime install failed" in result.stderr


def test_claude_setup_reports_missing_installed_helper(tmp_path: Path) -> None:
    result = run_setup(
        tmp_path,
        tmp_path / "managed" / "venv",
        extra_env={"FAKE_SKIP_HELPER": "1"},
    )

    assert result.returncode == 1
    assert "installed helper missing or not executable" in result.stderr


def test_claude_setup_reports_broken_installed_helper(tmp_path: Path) -> None:
    result = run_setup(
        tmp_path,
        tmp_path / "managed" / "venv",
        extra_env={"FAKE_BROKEN_HELPER": "1"},
    )

    assert result.returncode == 1
    assert "installed helper interpreter not executable" in result.stderr


def test_claude_setup_clears_only_verified_incomplete_venv(tmp_path: Path) -> None:
    venv = tmp_path / "managed" / "venv"
    venv.mkdir(parents=True)
    (venv / "pyvenv.cfg").write_text("home = /usr/bin\n", encoding="utf-8")

    result = run_setup(tmp_path, venv)

    assert result.returncode == 0, result.stderr
    assert "--clear" in (tmp_path / "python.log").read_text(encoding="utf-8")
    assert (venv / "bin" / "inter-agent-claude").is_file()


def test_claude_setup_does_not_clear_missing_venv(tmp_path: Path) -> None:
    venv = tmp_path / "managed" / "venv"

    result = run_setup(tmp_path, venv)

    assert result.returncode == 0, result.stderr
    log = (tmp_path / "python.log").read_text(encoding="utf-8")
    assert "-m venv " + str(venv) in log
    assert "--clear" not in log


def test_claude_setup_reuses_healthy_venv_without_clear(tmp_path: Path) -> None:
    venv = tmp_path / "managed" / "venv"
    helper = venv / "bin" / "inter-agent-claude"
    helper.parent.mkdir(parents=True)
    (venv / "pyvenv.cfg").write_text("home = /usr/bin\n", encoding="utf-8")
    helper.write_text("#!/bin/sh\nprintf healthy\\n", encoding="utf-8")
    helper.chmod(0o755)

    result = run_setup(tmp_path, venv)

    assert result.returncode == 0, result.stderr
    assert "--clear" not in (tmp_path / "python.log").read_text(encoding="utf-8")


def test_claude_setup_refuses_unrecognized_existing_directory(tmp_path: Path) -> None:
    venv = tmp_path / "managed" / "venv"
    venv.mkdir(parents=True)
    marker = venv / "must-remain.txt"
    marker.write_text("do not clear", encoding="utf-8")

    result = run_setup(tmp_path, venv)

    assert result.returncode == 2
    assert "manual inspection required" in result.stderr
    assert marker.read_text(encoding="utf-8") == "do not clear"


def test_claude_setup_refuses_empty_target(tmp_path: Path) -> None:
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    fake_python = fake_bin / "python3"
    _make_fake_python(fake_python, tmp_path / "python.log")
    result = subprocess.run(
        ["bash", str(SETUP), "--yes", "--venv", ""],
        env={
            "HOME": str(tmp_path / "home"),
            "PATH": f"{fake_bin}:/usr/bin:/bin",
            "FAKE_PYTHON_LOG": str(tmp_path / "python.log"),
        },
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert "managed venv path is empty" in result.stderr
    assert not (tmp_path / "home").exists()


def test_claude_setup_refuses_dot_segment_target(tmp_path: Path) -> None:
    result = run_setup(tmp_path, tmp_path / "managed" / ".." / "managed")

    assert result.returncode == 2
    assert "unsafe managed venv path" in result.stderr


def test_claude_setup_refuses_unsafe_target(tmp_path: Path) -> None:
    result = run_setup(tmp_path, Path("/tmp"))

    assert result.returncode == 2
    assert "unsafe managed venv path" in result.stderr
    assert not (tmp_path / "python.log").read_text(encoding="utf-8")


def test_claude_setup_refuses_symlink_target(tmp_path: Path) -> None:
    actual = tmp_path / "actual"
    actual.mkdir()
    (actual / "pyvenv.cfg").write_text("home = /usr/bin\n", encoding="utf-8")
    link = tmp_path / "managed"
    link.symlink_to(actual, target_is_directory=True)

    result = run_setup(tmp_path, link)

    assert result.returncode == 2
    assert "symlink" in result.stderr
    assert (actual / "pyvenv.cfg").is_file()
