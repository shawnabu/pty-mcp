"""PTY session management."""

import asyncio
import os
import pty
import re
import signal
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .config import SessionConfig


# ANSI escape sequence pattern
# Matches: ESC[...m (colors), ESC[...H (cursor), ESC]...\x07 (OSC), etc.
ANSI_ESCAPE_PATTERN = re.compile(
    r'\x1b'  # ESC character
    r'(?:'  # Non-capturing group for alternatives
    r'\[[0-9;]*[A-Za-z]'  # CSI sequences: ESC[...letter
    r'|\][^\x07]*\x07'  # OSC sequences: ESC]...\x07
    r'|\][^\x1b]*\x1b\\'  # OSC sequences: ESC]...\x1b\\
    r'|\([0-9A-Za-z]'  # Charset sequences: ESC(X
    r'|\)[0-9A-Za-z]'  # Charset sequences: ESC)X
    r'|[=>]'  # Other escape sequences
    r')'
)


def strip_ansi_codes(text: str) -> str:
    """
    Remove ANSI escape codes and other unprintable characters from text.
    
    Args:
        text: Text potentially containing ANSI codes
        
    Returns:
        Text with ANSI codes removed
    """
    # Remove ANSI escape sequences
    text = ANSI_ESCAPE_PATTERN.sub('', text)
    
    # Remove other control characters except \n, \r, \t
    text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]', '', text)
    
    return text


@dataclass
class PTYSession:
    """Manages a single PTY session."""

    session_id: str
    config: SessionConfig
    log_dir: Optional[str] = None
    pid: int = field(init=False)
    fd: int = field(init=False)
    buffer: deque[str] = field(init=False)
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    _running: bool = field(default=False, init=False)
    _read_task: Optional[asyncio.Task] = field(default=None, init=False)
    _pending_output: str = field(default="", init=False)
    _log_file: Optional[object] = field(default=None, init=False)

    def __post_init__(self) -> None:
        self.buffer = deque(maxlen=self.config.buffer_size)

    async def start(self) -> None:
        """Start the PTY session."""
        pid, fd = pty.fork()

        if pid == 0:
            # Child process
            os.chdir(self.config.cwd)
            # Build argv: [program_name, *additional_args]
            argv = [self.config.command] + self.config.args
            os.execvp(self.config.command, argv)
        else:
            # Parent process
            self.pid = pid
            self.fd = fd
            self._running = True

            # Set non-blocking mode
            os.set_blocking(fd, False)

            # Open log file if logging enabled
            if self.log_dir:
                command_name = os.path.basename(self.config.command)
                log_filename = f"pty_{command_name}_{self.session_id}.log"
                log_path = os.path.join(self.log_dir, log_filename)
                self._log_file = open(log_path, 'w', encoding='utf-8', buffering=1)

            # Start background reader
            self._read_task = asyncio.create_task(self._read_loop())

    async def _read_loop(self) -> None:
        """Continuously read from PTY and buffer output."""
        loop = asyncio.get_event_loop()

        while self._running:
            try:
                data = await loop.run_in_executor(None, self._read_chunk)
                if data:
                    self._pending_output += data
                    # Add complete lines to buffer
                    while "\n" in self._pending_output:
                        line, self._pending_output = self._pending_output.split(
                            "\n", 1
                        )
                        self.buffer.append(line)
                        # Write to log file immediately
                        if self._log_file:
                            self._log_file.write(line + "\n")
                    self.last_activity = datetime.now()
            except OSError:
                break
            await asyncio.sleep(0.01)

    def _read_chunk(self) -> str:
        """Read available data from PTY."""
        try:
            data = os.read(self.fd, 4096)
            decoded = data.decode("utf-8", errors="replace")
            # Strip ANSI codes and unprintable characters
            return strip_ansi_codes(decoded)
        except BlockingIOError:
            return ""
        except OSError:
            return ""

    async def run_command(
        self, command: str, timeout: float = 30.0
    ) -> tuple[str, bool]:
        """
        Run a command and wait for completion using sentinel.

        Returns tuple of (output, completed).
        If completed is False, command timed out.
        """
        sentinel = f"__PTY_DONE_{uuid.uuid4().hex[:8]}__"
        sentinel_cmd = self.config.sentinel_command.format(sentinel=sentinel)

        # Clear pending output tracking for this command
        start_buffer_len = len(self.buffer)

        # Send command followed by sentinel command
        full_command = f"{command}\n{sentinel_cmd}\n"
        await self._write(full_command)

        # Wait for sentinel to appear
        output_lines: list[str] = []
        start_time = asyncio.get_event_loop().time()

        while True:
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > timeout:
                # Timeout - return what we have
                return "\n".join(output_lines), False

            # Check buffer for new lines since command started
            current_buffer = list(self.buffer)
            new_lines = current_buffer[start_buffer_len:]

            # Look for sentinel
            for i, line in enumerate(new_lines):
                if sentinel in line:
                    # Skip if this is the command echo (contains the echo command itself)
                    # Real sentinel output is just the sentinel value, not "echo <sentinel>"
                    stripped = line.strip()
                    if stripped == sentinel_cmd.strip() or stripped.endswith(sentinel_cmd.strip()):
                        continue  # This is the command echo, not the actual sentinel output
                    
                    # Found sentinel - return everything before it
                    output_lines = new_lines[:i]
                    # Filter out the command echo and sentinel command echo
                    output_lines = self._filter_command_echo(
                        output_lines, command, sentinel_cmd
                    )
                    return "\n".join(output_lines), True

            output_lines = new_lines
            await asyncio.sleep(0.05)

    def _filter_command_echo(
        self, lines: list[str], command: str, sentinel_cmd: str
    ) -> list[str]:
        """Filter out command echoes from output."""
        result = []
        for line in lines:
            stripped = line.strip()
            # Skip lines that are just the command or sentinel command
            if stripped == command.strip() or stripped == sentinel_cmd.strip():
                continue
            # Skip prompt lines that end with the command
            if stripped.endswith(command.strip()):
                continue
            if stripped.endswith(sentinel_cmd.strip()):
                continue
            result.append(line)
        return result

    async def send_keys(self, keys: str) -> None:
        """Send raw input to the PTY."""
        await self._write(keys)
        self.last_activity = datetime.now()

    async def _write(self, data: str) -> None:
        """Write data to PTY."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, os.write, self.fd, data.encode("utf-8"))
        self.last_activity = datetime.now()

    def get_buffer(self, lines: Optional[int] = None) -> str:
        """Get buffer contents, optionally last N lines."""
        buffer_list = list(self.buffer)
        if lines is not None:
            buffer_list = buffer_list[-lines:]
        return "\n".join(buffer_list)

    async def stop(self) -> None:
        """Stop the PTY session."""
        self._running = False

        if self._read_task:
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass

        # Close log file
        if self._log_file:
            try:
                self._log_file.close()
            except:
                pass

        try:
            os.close(self.fd)
        except OSError:
            pass

        try:
            os.kill(self.pid, signal.SIGTERM)
            # Give it a moment to terminate gracefully
            await asyncio.sleep(0.1)
            os.kill(self.pid, signal.SIGKILL)
        except (OSError, ProcessLookupError):
            pass

        # Reap the child process
        try:
            os.waitpid(self.pid, os.WNOHANG)
        except ChildProcessError:
            pass

    def is_alive(self) -> bool:
        """Check if the PTY process is still running."""
        try:
            os.kill(self.pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False


class SessionManager:
    """Manages multiple PTY sessions."""

    def __init__(self, max_sessions: int = 10, log_dir: Optional[str] = None) -> None:
        self.max_sessions = max_sessions
        self.log_dir = log_dir
        self.sessions: dict[str, PTYSession] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
        
        # Validate log_dir if provided
        if self.log_dir and not os.path.isdir(self.log_dir):
            raise ValueError(f"Log directory does not exist: {self.log_dir}")

    async def start(self) -> None:
        """Start the session manager."""
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop(self) -> None:
        """Stop all sessions and cleanup."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        for session in list(self.sessions.values()):
            await session.stop()
        self.sessions.clear()

    async def _cleanup_loop(self) -> None:
        """Periodically clean up timed-out sessions."""
        while True:
            await asyncio.sleep(60)  # Check every minute
            now = datetime.now()

            for session_id, session in list(self.sessions.items()):
                # Check timeout
                idle_seconds = (now - session.last_activity).total_seconds()
                if idle_seconds > session.config.timeout_session:
                    await session.stop()
                    del self.sessions[session_id]

                # Check if process died
                elif not session.is_alive():
                    await session.stop()
                    del self.sessions[session_id]

    async def create_session(self, config: SessionConfig) -> PTYSession:
        """Create a new PTY session."""
        if len(self.sessions) >= self.max_sessions:
            raise RuntimeError(
                f"Maximum sessions ({self.max_sessions}) reached"
            )

        session_id = uuid.uuid4().hex[:12]
        session = PTYSession(session_id=session_id, config=config, log_dir=self.log_dir)
        await session.start()

        self.sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[PTYSession]:
        """Get a session by ID."""
        return self.sessions.get(session_id)

    async def remove_session(self, session_id: str) -> bool:
        """Stop and remove a session."""
        session = self.sessions.pop(session_id, None)
        if session:
            await session.stop()
            return True
        return False

    def list_sessions(self) -> list[dict]:
        """List all active sessions."""
        return [
            {
                "session_id": session.session_id,
                "command": session.config.command,
                "cwd": session.config.cwd,
                "created_at": session.created_at.isoformat(),
                "last_activity": session.last_activity.isoformat(),
                "is_alive": session.is_alive(),
            }
            for session in self.sessions.values()
        ]
