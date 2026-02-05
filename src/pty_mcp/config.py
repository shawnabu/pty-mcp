"""Configuration for PTY-MCP server."""

from dataclasses import dataclass, field
import os


@dataclass
class SessionConfig:
    """Configuration for a PTY session."""

    shell: str = field(default_factory=lambda: os.environ.get("SHELL", "/bin/bash"))
    shell_args: list[str] = field(default_factory=list)  # Additional arguments for shell
    cwd: str = field(default_factory=os.getcwd)
    timeout_seconds: int = 1800  # 30 minutes idle timeout
    buffer_size: int = 1000  # lines to keep in scrollback
    sentinel_command: str = "echo {sentinel}"  # command to echo sentinel


@dataclass
class ServerConfig:
    """Configuration for the MCP server."""

    max_sessions: int = 10
    default_command_timeout: float = 30.0  # seconds to wait for command completion
