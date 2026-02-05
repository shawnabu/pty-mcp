# Agent Guide for PTY-MCP

This document provides essential information for AI agents working on the PTY-MCP codebase.

## Project Overview

PTY-MCP is an MCP (Model Context Protocol) server that exposes PTY (pseudo-terminal) sessions for AI agents. It enables programmatic control of shell sessions and REPLs through the Model Context Protocol.

**Key Purpose:** Allow AI agents to start and interact with any command-line program (bash, python, tcl, custom binaries, etc.) through a clean API.

## Architecture

```
src/pty_mcp/
├── server.py         # Main MCP server entry point
├── tools.py          # MCP tool definitions (API surface)
├── session.py        # PTY session management (core logic)
├── config.py         # Configuration dataclasses
└── __init__.py

tests/
├── test_tools.py     # Integration tests for MCP tools
├── test_session.py   # Unit tests for session management
└── test_logging.py   # Tests for logging functionality
```

## Key Concepts

### 1. Sessions
- Each session wraps a PTY running a command (shell, REPL, or binary)
- Sessions have unique IDs and maintain a scrollback buffer
- Sessions auto-cleanup on timeout or process death

### 2. Command Execution
- Uses **sentinel-based completion detection** (not exit codes)
- Sends command + unique sentinel, waits for sentinel in output
- Supports nested REPLs by changing sentinel command (e.g., `echo` for bash, `print()` for Python)

### 3. Command String Parsing
- `command` parameter accepts strings like `"somebinary -a -b --args"`
- Auto-parses using `shlex.split()` if `args` parameter not provided
- Explicit `args` parameter overrides parsing (use for complex cases)

## Development Workflow

### Package Manager: uv

**This project uses `uv`, NOT pip or poetry.**

```bash
# Install dependencies
uv sync

# Run tests (ALWAYS use this)
uv run pytest tests/ -v

# Run specific test file
uv run pytest tests/test_tools.py -v

# Run specific test
uv run pytest tests/test_tools.py::test_command_string_parsing -v

# Run the server
uv run pty-mcp
```

### Testing Philosophy

**IMPORTANT:** When implementing features or fixing bugs:
- ✅ **DO:** Create pytest tests in the `tests/` directory
- ❌ **DON'T:** Create one-off Python scripts for testing
- ❌ **DON'T:** Use `python3 script.py` unless the user specifically asks for a script

**Why?**
- Tests are permanent documentation of behavior
- Tests prevent regressions
- Tests run in CI/CD
- One-off scripts are throwaway code

**Example - User asks to test a feature:**
```bash
# CORRECT
uv run pytest tests/test_new_feature.py -v

# INCORRECT (unless user specifically asks for a script)
python3 test_script.py
```

## Important Implementation Details

### 1. Parameter Naming
- Use `command` (not `shell`) - it can be any executable
- Use `args` (not `shell_args`) - clearer and shorter
- Command strings are auto-parsed: `"binary -a -b"` → `command="binary"`, `args=["-a", "-b"]`

### 2. PTY Handling
- Uses `os.forkpty()` and `os.execvp()`
- Requires command and args to be separate for `execvp()`
- Non-blocking reads with `asyncio` event loop
- Process management uses `os.kill()` with specific PIDs (never `pkill`/`killall`)

### 3. Sentinel Commands
- Default: `echo {sentinel}` (for shells)
- Python REPL: `print('{sentinel}')`
- Node.js REPL: `console.log('{sentinel}')`
- Tcl: `puts {sentinel}`
- Must handle command echo filtering (shells echo input)

### 4. Logging
- Optional real-time logging to disk (`--log-dir` option)
- Logs named: `{command_name}_{session_id}.log`
- Buffered writes (line-buffered for real-time tailing)

## Common Tasks

### Adding a New MCP Tool

1. Add tool definition in `tools.py` → `list_tools()`
2. Add handler in `tools.py` → `call_tool()`
3. Implement handler function: `async def _tool_name(...)`
4. Add tests in `tests/test_tools.py`
5. Update README.md with tool documentation

### Modifying Session Behavior

1. Edit `session.py` → `PTYSession` class
2. Add unit tests in `tests/test_session.py`
3. Run tests: `uv run pytest tests/test_session.py -v`

### Changing Configuration

1. Edit `config.py` dataclasses
2. Update all references in `tools.py` and `session.py`
3. Update tests to use new config
4. Update README.md

## Testing Guidelines

### Test Structure
```python
@pytest.mark.asyncio
async def test_feature_name(manager):  # manager fixture auto-provided
    """Clear description of what is being tested."""
    # Arrange
    result = await _start_session(manager, {"command": "/bin/bash"})
    session_id = extract_session_id(result)
    
    # Act
    result = await _run_command(manager, {
        "session_id": session_id,
        "command": "echo test"
    })
    
    # Assert
    assert "test" in result[0].text
```

### Running Tests
```bash
# Run all tests
uv run pytest tests/ -v

# Run with coverage
uv run pytest tests/ -v --cov=src/pty_mcp

# Run specific test file
uv run pytest tests/test_tools.py -v

# Run tests matching pattern
uv run pytest tests/ -k "command_parsing" -v
```

### Test Fixtures
- `manager` fixture (in `conftest.py`): Provides SessionManager instance
- All fixtures handle cleanup automatically
- Tests are isolated (each gets fresh state)

## Code Style

- Use `async`/`await` consistently (this is an async codebase)
- Type hints on function signatures
- Docstrings for public methods and non-obvious logic
- Keep functions focused and single-purpose
- Avoid over-commenting obvious code

## Common Pitfalls

1. **Don't use `shell=True` in subprocess calls** - We use PTY/execvp for a reason
2. **Don't forget sentinel command filtering** - Shells echo commands
3. **Don't use blocking I/O** - Use `asyncio` and `run_in_executor()`
4. **Don't hardcode shell assumptions** - This works with any command
5. **Don't create test scripts** - Use pytest tests in `tests/`

## Debugging Tips

### Running tests with output
```bash
# Show print statements
uv run pytest tests/ -v -s

# Show detailed failure info
uv run pytest tests/ -v --tb=long

# Drop into pdb on failure
uv run pytest tests/ -v --pdb
```

### Testing individual sessions
```python
# Add to tests/test_session.py and run with pytest
@pytest.mark.asyncio
async def test_debug_scenario():
    config = SessionConfig(command="/bin/bash")
    session = PTYSession(session_id="debug", config=config)
    await session.start()
    
    # Your debug code here
    output, completed = await session.run_command("your command")
    print(f"Output: {output}")
    print(f"Completed: {completed}")
    
    await session.stop()
```

### Checking session logs
```bash
# Enable logging for debugging
uv run pty-mcp --log-dir /tmp/pty-logs

# Watch logs in real-time
tail -f /tmp/pty-logs/*.log
```

## Dependencies

Managed by `uv` via `pyproject.toml`:
- `mcp` - Model Context Protocol SDK
- `pytest`, `pytest-asyncio` - Testing framework
- No heavy dependencies (intentionally minimal)

## Summary for Agents

**When working on this codebase:**
1. Use `uv run pytest` to run tests
2. Create pytest tests, not scripts
3. Command parameters: `command` (any executable) + `args` (optional)
4. Sessions use sentinel-based completion detection
5. Everything is async - use `async`/`await`
6. Test files go in `tests/`, match pattern `test_*.py`
7. Keep the codebase clean and minimal

**Quick validation after changes:**
```bash
uv run pytest tests/ -v  # All tests must pass
```
