"""Unit tests for PTY session management."""

import pytest
import asyncio

from pty_mcp.config import SessionConfig
from pty_mcp.session import PTYSession, SessionManager


@pytest.mark.asyncio
async def test_session_start_stop():
    """Test basic session lifecycle."""
    config = SessionConfig(shell="/bin/bash")
    session = PTYSession(session_id="test1", config=config)

    await session.start()
    assert session.is_alive()

    await session.stop()
    await asyncio.sleep(0.1)
    assert not session.is_alive()


@pytest.mark.asyncio
async def test_run_simple_command():
    """Test running a simple echo command."""
    config = SessionConfig(shell="/bin/bash")
    session = PTYSession(session_id="test2", config=config)

    await session.start()
    await asyncio.sleep(0.2)  # Let shell initialize

    output, completed = await session.run_command("echo hello", timeout=5.0)

    assert completed
    assert "hello" in output

    await session.stop()


@pytest.mark.asyncio
async def test_run_command_with_output():
    """Test command that produces multi-line output."""
    config = SessionConfig(shell="/bin/bash")
    session = PTYSession(session_id="test3", config=config)

    await session.start()
    await asyncio.sleep(0.2)

    output, completed = await session.run_command("echo -e 'line1\\nline2\\nline3'", timeout=5.0)

    assert completed
    assert "line1" in output
    assert "line2" in output
    assert "line3" in output

    await session.stop()


@pytest.mark.asyncio
async def test_get_buffer():
    """Test buffer retrieval."""
    config = SessionConfig(shell="/bin/bash", buffer_size=100)
    session = PTYSession(session_id="test4", config=config)

    await session.start()
    await asyncio.sleep(0.2)

    await session.run_command("echo buffer_test", timeout=5.0)

    buffer = session.get_buffer()
    assert "buffer_test" in buffer

    await session.stop()


@pytest.mark.asyncio
async def test_get_buffer_last_n_lines():
    """Test getting last N lines from buffer."""
    config = SessionConfig(shell="/bin/bash", buffer_size=100)
    session = PTYSession(session_id="test5", config=config)

    await session.start()
    await asyncio.sleep(0.2)

    for i in range(5):
        await session.run_command(f"echo line{i}", timeout=5.0)

    buffer = session.get_buffer(lines=2)
    lines = buffer.strip().split("\n")
    assert len(lines) <= 2

    await session.stop()


@pytest.mark.asyncio
async def test_send_keys():
    """Test sending raw keys."""
    config = SessionConfig(shell="/bin/bash")
    session = PTYSession(session_id="test6", config=config)

    await session.start()
    await asyncio.sleep(0.2)

    await session.send_keys("echo raw_input\n")
    await asyncio.sleep(0.5)

    buffer = session.get_buffer()
    assert "raw_input" in buffer

    await session.stop()


@pytest.mark.asyncio
async def test_session_manager_create_remove():
    """Test session manager lifecycle."""
    manager = SessionManager(max_sessions=5)
    await manager.start()

    config = SessionConfig()
    session = await manager.create_session(config)

    assert session.session_id in [s["session_id"] for s in manager.list_sessions()]

    removed = await manager.remove_session(session.session_id)
    assert removed

    assert session.session_id not in [s["session_id"] for s in manager.list_sessions()]

    await manager.stop()


@pytest.mark.asyncio
async def test_session_manager_max_sessions():
    """Test max sessions limit."""
    manager = SessionManager(max_sessions=2)
    await manager.start()

    config = SessionConfig()
    await manager.create_session(config)
    await manager.create_session(config)

    with pytest.raises(RuntimeError, match="Maximum sessions"):
        await manager.create_session(config)

    await manager.stop()


@pytest.mark.asyncio
async def test_python_repl():
    """Test running commands in Python REPL."""
    config = SessionConfig(
        shell="/bin/bash",
        sentinel_command="print('{sentinel}')",
    )
    session = PTYSession(session_id="test_python", config=config)

    await session.start()
    await asyncio.sleep(0.2)

    # Start Python
    await session.send_keys("python3\n")
    await asyncio.sleep(0.5)

    # Run a Python command
    output, completed = await session.run_command("print('hello from python')", timeout=5.0)

    assert completed
    assert "hello from python" in output

    # Exit Python
    await session.send_keys("exit()\n")
    await asyncio.sleep(0.2)

    await session.stop()


@pytest.mark.asyncio
async def test_shell_with_args():
    """Test starting a shell with command-line arguments."""
    # Start bash with -c option to run a command
    config = SessionConfig(
        shell="/bin/bash",
        shell_args=["-c", "echo 'test_arg_output'; exec bash"],
        buffer_size=100,
    )
    session = PTYSession(session_id="test_args", config=config)

    await session.start()
    await asyncio.sleep(0.3)

    buffer = session.get_buffer()
    assert "test_arg_output" in buffer

    await session.stop()
