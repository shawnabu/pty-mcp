# PTY-MCP

MCP server exposing PTY (pseudo-terminal) sessions for AI agents. Enables programmatic control of shell sessions and REPLs through the Model Context Protocol.

## Features

- Start and manage multiple PTY sessions
- Run commands with sentinel-based completion detection
- Automatic ANSI escape code filtering (colors, cursor control, etc.)
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
uv run pty-mcp --max-sessions 10 --log-dir /path/to/logs
```

The `--log-dir` option enables real-time session logging. When specified, each session's output is written immediately to a log file named `pty_<command_name>_<session_id>.log` (e.g., `pty_bash_3a4b5c6d7e8f.log`). The directory must exist; the server will error if it doesn't. You can watch logs in real-time with `tail -f /path/to/logs/*.log`.

### MCP Tools

#### `start_session`

Start a new PTY session with any command or shell.

**Parameters:**
- `command` (optional): Command/binary to execute (default: `$SHELL` or `/bin/bash`). Can be any executable like `bash`, `python3`, `tcl`, `somebinary -a -b`, etc. If `args` is not provided, the command string will be automatically parsed to extract arguments.
- `args` (optional): List of arguments to pass to the command. If omitted, arguments will be parsed from the `command` string. Explicitly provide this when arguments contain spaces or special characters.
- `cwd` (optional): Working directory
- `timeout_session` (optional): Idle timeout (default: 86400)
- `buffer_size` (optional): Scrollback buffer lines (default: 1000)
- `sentinel_command` (optional): Command to echo sentinel (default: `echo {sentinel}`)

**Returns:** Session ID

**Examples:**
```python
# Start default shell (bash)
start_session()

# Start Python REPL
start_session(command="python3")

# Start custom binary with arguments (auto-parsed)
start_session(command="somebinary -a -b --args")

# Start with explicit args (for complex arguments)
start_session(command="somebinary", args=["-a", "-b", "--args"])

# Start Tcl shell in specific directory
start_session(command="tclsh", cwd="/path/to/project")
```

#### `run_command`

Run a command and wait for completion.

**Parameters:**
- `session_id` (required): Session ID from `start_session`
- `command` (required): Command to run
- `timeout` (optional): Timeout in seconds (default: 1800)

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

## Output Filtering

PTY-MCP automatically filters ANSI escape sequences and unprintable characters from all output. This ensures clean, parseable text without terminal formatting codes.

**Filtered sequences:**
- ANSI color codes (e.g., `\x1b[31m` for red text)
- Cursor movement codes (e.g., `\x1b[2J` for clear screen)
- Text formatting (bold, italic, underline)
- OSC sequences (terminal titles, hyperlinks)
- Control characters (excluding newline, tab)

**Line ending normalization:**
- `\r\n` (Windows/DOS) → `\n` (Unix)
- Standalone `\r` (progress bars, spinners) → keeps only final state

**Examples:**
- `ls --color=always` - colors stripped automatically
- `"Progress: 10%\rProgress: 100%"` → `"Progress: 100%"` (progress bars)
- `"Line1\r\nLine2\r\n"` → `"Line1\nLine2\n"` (normalized line endings)
- Colored bash prompts have formatting removed

## Development

```bash
# Install dependencies
uv sync

# Run tests
uv run pytest tests/ -v
```

## License

MIT
