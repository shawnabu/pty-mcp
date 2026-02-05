# PTY-MCP

MCP server exposing PTY (pseudo-terminal) sessions for AI agents. Enables programmatic control of shell sessions and REPLs through the Model Context Protocol.

## Features

- Start and manage multiple PTY sessions
- Run commands with sentinel-based completion detection
- Works with any shell (bash, zsh, tcsh, fish, etc.)
- Works with nested REPLs (Python, Node, Tcl, etc.)
- Configurable session timeout and buffer size
- Raw input support for interactive applications

## Installation

```bash
uv add pty-mcp
```

## Usage

### As an MCP Server

Add to your MCP client configuration:

```json
{
  "mcpServers": {
    "pty": {
      "command": "uv",
      "args": ["run", "pty-mcp"]
    }
  }
}
```

Or run directly:

```bash
uv run pty-mcp --max-sessions 10
```

### MCP Tools

#### `start_session`

Start a new PTY session.

**Parameters:**
- `shell` (optional): Shell to use (default: `$SHELL` or `/bin/bash`)
- `cwd` (optional): Working directory
- `timeout_seconds` (optional): Idle timeout (default: 1800)
- `buffer_size` (optional): Scrollback buffer lines (default: 1000)
- `sentinel_command` (optional): Command to echo sentinel (default: `echo {sentinel}`)

**Returns:** Session ID

#### `run_command`

Run a command and wait for completion.

**Parameters:**
- `session_id` (required): Session ID from `start_session`
- `command` (required): Command to run
- `timeout` (optional): Timeout in seconds (default: 30)

**Returns:** Command output

#### `send_keys`

Send raw input without waiting for completion.

**Parameters:**
- `session_id` (required): Session ID
- `keys` (required): Raw input (use `\n` for Enter, `\x03` for Ctrl+C)

#### `get_buffer`

Get scrollback buffer contents.

**Parameters:**
- `session_id` (required): Session ID
- `lines` (optional): Number of lines from end

**Returns:** Buffer contents

#### `stop_session`

Stop and clean up a session.

**Parameters:**
- `session_id` (required): Session ID to stop

#### `set_sentinel`

Change the sentinel command for a session. Use when switching between shells/REPLs.

**Parameters:**
- `session_id` (required): Session ID
- `sentinel_command` (required): New sentinel command template with `{sentinel}` placeholder

#### `list_sessions`

List all active sessions with metadata.

## Working with REPLs

When switching from a shell to a REPL (or between REPLs), use `set_sentinel` to update the sentinel command:

```python
# Start with bash (default sentinel: echo {sentinel})
session_id = start_session()

# Run some bash commands
run_command(session_id, "ls -la")

# Switch to Python REPL
send_keys(session_id, "python3\n")
set_sentinel(session_id, "print('{sentinel}')")

# Now run Python commands
run_command(session_id, "print('hello from python')")
run_command(session_id, "2 + 2")

# Exit Python and switch back to bash
send_keys(session_id, "exit()\n")
set_sentinel(session_id, "echo {sentinel}")
```

**Common sentinel commands:**
- Bash/sh/zsh: `echo {sentinel}`
- Python: `print('{sentinel}')`
- Node.js: `console.log('{sentinel}')`
- Tcl: `puts {sentinel}`
- Ruby (irb): `puts '{sentinel}'`

## Development

```bash
# Install dependencies
uv sync

# Run tests
uv run pytest tests/ -v
```

## License

MIT
