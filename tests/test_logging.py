"""Tests for session logging functionality."""

import tempfile
from pathlib import Path

import pytest

from pty_mcp.config import SessionConfig
from pty_mcp.session import SessionManager


@pytest.mark.asyncio
async def test_log_dir_validation():
    """Test that SessionManager raises error for non-existent log directory."""
    with pytest.raises(ValueError, match="Log directory does not exist"):
        SessionManager(log_dir="/nonexistent/directory")


@pytest.mark.asyncio
async def test_session_logging():
    """Test that session logs are written when log_dir is specified."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = SessionManager(max_sessions=5, log_dir=tmpdir)
        await manager.start()

        config = SessionConfig(command="/bin/bash")
        session = await manager.create_session(config)
        session_id = session.session_id

        # Run a command
        output, completed = await session.run_command("echo 'Hello World'")
        assert completed
        assert "Hello World" in output

        # Stop session (should write log)
        await session.stop()

        # Check log file exists
        log_file = Path(tmpdir) / f"pty_bash_{session_id}.log"
        assert log_file.exists()

        # Check log content
        content = log_file.read_text()
        assert len(content) > 0
        assert "Hello World" in content

        await manager.stop()


@pytest.mark.asyncio
async def test_no_logging_when_disabled():
    """Test that no logs are written when log_dir is None."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = SessionManager(max_sessions=5, log_dir=None)
        await manager.start()

        config = SessionConfig(command="/bin/bash", cwd=tmpdir)
        session = await manager.create_session(config)
        session_id = session.session_id

        await session.run_command("echo 'Test'")
        await session.stop()

        # Check no log files created in temp directory
        log_files = list(Path(tmpdir).glob("*.log"))
        assert len(log_files) == 0

        await manager.stop()


@pytest.mark.asyncio
async def test_log_filename_format():
    """Test that log filenames follow the correct format."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = SessionManager(log_dir=tmpdir)
        await manager.start()

        # Test with different commands
        for command_path in ["/bin/bash", "/bin/sh"]:
            config = SessionConfig(command=command_path)
            session = await manager.create_session(config)
            session_id = session.session_id
            command_name = Path(command_path).name

            await session.run_command("echo 'test'")
            await session.stop()

            # Check log filename format
            log_file = Path(tmpdir) / f"pty_{command_name}_{session_id}.log"
            assert log_file.exists()

        await manager.stop()


@pytest.mark.asyncio
async def test_realtime_logging():
    """Test that logs are written in real-time, not just at session end."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = SessionManager(log_dir=tmpdir)
        await manager.start()

        config = SessionConfig(command="/bin/bash")
        session = await manager.create_session(config)
        session_id = session.session_id

        log_file = Path(tmpdir) / f"pty_bash_{session_id}.log"
        
        # Run first command
        await session.run_command("echo 'First message'")
        
        # Log file should exist and contain first message
        assert log_file.exists()
        content1 = log_file.read_text()
        assert "First message" in content1
        
        # Run second command
        await session.run_command("echo 'Second message'")
        
        # Log should now contain both messages (before session.stop())
        content2 = log_file.read_text()
        assert "First message" in content2
        assert "Second message" in content2
        
        await session.stop()
        await manager.stop()

