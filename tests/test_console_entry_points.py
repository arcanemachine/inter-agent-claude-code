from __future__ import annotations

import tomllib
from collections.abc import Callable, Sequence
from pathlib import Path

import pytest

from inter_agent_claude.cli import main as claude_main

ROOT = Path(__file__).resolve().parents[1]


def test_only_claude_console_script_is_declared() -> None:
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    scripts = config["project"]["scripts"]
    assert scripts == {"inter-agent-claude": "inter_agent_claude.cli:main"}


def test_claude_console_script_help_lists_program_name(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        claude_main(["--help"])

    assert exc_info.value.code == 0
    assert "inter-agent-claude" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("command_name", "main"),
    [("inter-agent-claude", claude_main)],
)
def test_command_help_output(
    command_name: str,
    main: Callable[[Sequence[str] | None], int],
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])

    assert exc_info.value.code == 0
    assert command_name in capsys.readouterr().out
