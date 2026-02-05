"""Integration tests for MCP tools."""

import pytest
import pytest_asyncio
import asyncio

from pty_mcp.session import SessionManager
from pty_mcp.tools import (
    _start_session,
    _run_command,
    _send_keys,
    _get_buffer,
    _stop_session,
    _set_sentinel,
    _list_sessions,
)


@pytest_asyncio.fixture
async def manager():
    """Create and start a session manager."""
    mgr = SessionManager(max_sessions=5)
    await mgr.start()
    yield mgr
    await mgr.stop()


@pytest.mark.asyncio
async def test_start_session_tool(manager):
    """Test start_session tool."""
    result = await _start_session(manager, {})

    assert len(result) == 1
    assert "Session started:" in result[0].text

    # Extract session_id
    session_id = result[0].text.split("\n")[0].split(": ")[1]
    assert len(session_id) == 12


@pytest.mark.asyncio
async def test_run_command_tool(manager):
    """Test run_command tool."""
    # Start session
    result = await _start_session(manager, {})
    session_id = result[0].text.split("\n")[0].split(": ")[1]

    await asyncio.sleep(0.2)

    # Run command
    result = await _run_command(
        manager, {"session_id": session_id, "command": "echo tool_test"}
    )

    assert len(result) == 1
    assert "tool_test" in result[0].text


@pytest.mark.asyncio
async def test_run_command_not_found(manager):
    """Test run_command with invalid session."""
    result = await _run_command(
        manager, {"session_id": "invalid123", "command": "echo test"}
    )

    assert "Session not found" in result[0].text


@pytest.mark.asyncio
async def test_send_keys_tool(manager):
    """Test send_keys tool."""
    result = await _start_session(manager, {})
    session_id = result[0].text.split("\n")[0].split(": ")[1]

    await asyncio.sleep(0.2)

    result = await _send_keys(
        manager, {"session_id": session_id, "keys": "echo keys_test\\n"}
    )

    assert result[0].text == "Keys sent"


@pytest.mark.asyncio
async def test_get_buffer_tool(manager):
    """Test get_buffer tool."""
    result = await _start_session(manager, {})
    session_id = result[0].text.split("\n")[0].split(": ")[1]

    await asyncio.sleep(0.2)

    await _run_command(
        manager, {"session_id": session_id, "command": "echo buffer_content"}
    )

    result = await _get_buffer(manager, {"session_id": session_id})

    assert "buffer_content" in result[0].text


@pytest.mark.asyncio
async def test_stop_session_tool(manager):
    """Test stop_session tool."""
    result = await _start_session(manager, {})
    session_id = result[0].text.split("\n")[0].split(": ")[1]

    result = await _stop_session(manager, {"session_id": session_id})

    assert "Session stopped" in result[0].text

    # Verify session is gone
    result = await _stop_session(manager, {"session_id": session_id})
    assert "Session not found" in result[0].text


@pytest.mark.asyncio
async def test_list_sessions_tool(manager):
    """Test list_sessions tool."""
    # No sessions
    result = await _list_sessions(manager)
    assert "No active sessions" in result[0].text

    # Create sessions
    await _start_session(manager, {})
    await _start_session(manager, {})

    result = await _list_sessions(manager)
    assert "Active sessions:" in result[0].text


@pytest.mark.asyncio
async def test_custom_shell(manager):
    """Test starting session with custom shell."""
    result = await _start_session(manager, {"shell": "/bin/sh"})

    assert "Shell: /bin/sh" in result[0].text


@pytest.mark.asyncio
async def test_set_sentinel_tool(manager):
    """Test set_sentinel tool for switching REPLs."""
    result = await _start_session(manager, {})
    session_id = result[0].text.split("\n")[0].split(": ")[1]

    await asyncio.sleep(0.2)

    # Change sentinel for Python REPL
    result = await _set_sentinel(
        manager,
        {"session_id": session_id, "sentinel_command": "print('{sentinel}')"},
    )

    assert "Sentinel command updated" in result[0].text

    # Start Python
    await _send_keys(manager, {"session_id": session_id, "keys": "python3\\n"})
    await asyncio.sleep(0.5)

    # Run Python command with new sentinel
    result = await _run_command(
        manager,
        {"session_id": session_id, "command": "print('from_python')"},
    )

    assert "from_python" in result[0].text


@pytest.mark.asyncio
async def test_command_timeout(manager):
    """Test command timeout handling."""
    result = await _start_session(manager, {})
    session_id = result[0].text.split("\n")[0].split(": ")[1]

    await asyncio.sleep(0.2)

    # Run a command that will timeout (sleep longer than timeout)
    result = await _run_command(
        manager,
        {"session_id": session_id, "command": "sleep 10", "timeout": 0.5},
    )

    assert "TIMEOUT" in result[0].text
