"""MCP tool definitions for PTY sessions."""

from typing import Optional

from mcp.server import Server
from mcp.types import Tool, TextContent

from .config import SessionConfig
from .session import SessionManager


def register_tools(server: Server, session_manager: SessionManager) -> None:
    """Register all PTY tools with the MCP server."""

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="start_session",
                description="Start a new PTY session. Returns a session_id to use with other commands.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "shell": {
                            "type": "string",
                            "description": "Shell to use (default: $SHELL or /bin/bash)",
                        },
                        "cwd": {
                            "type": "string",
                            "description": "Working directory for the session",
                        },
                        "timeout_seconds": {
                            "type": "integer",
                            "description": "Idle timeout in seconds (default: 1800)",
                        },
                        "buffer_size": {
                            "type": "integer",
                            "description": "Scrollback buffer size in lines (default: 1000)",
                        },
                        "sentinel_command": {
                            "type": "string",
                            "description": "Command template to echo sentinel. Use {sentinel} placeholder. Default: 'echo {sentinel}'. For Python REPL: \"print('{sentinel}')\"",
                        },
                    },
                },
            ),
            Tool(
                name="run_command",
                description="Run a command in a PTY session and wait for completion. Uses sentinel-based detection to know when command finishes.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "string",
                            "description": "The session ID returned by start_session",
                        },
                        "command": {
                            "type": "string",
                            "description": "The command to run",
                        },
                        "timeout": {
                            "type": "number",
                            "description": "Timeout in seconds to wait for command completion (default: 30)",
                        },
                    },
                    "required": ["session_id", "command"],
                },
            ),
            Tool(
                name="send_keys",
                description="Send raw input to a PTY session without waiting for completion. Use for interactive input, Ctrl+C (send '\\x03'), etc.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "string",
                            "description": "The session ID",
                        },
                        "keys": {
                            "type": "string",
                            "description": "Raw input to send. Use \\n for Enter, \\x03 for Ctrl+C, etc.",
                        },
                    },
                    "required": ["session_id", "keys"],
                },
            ),
            Tool(
                name="get_buffer",
                description="Get the scrollback buffer from a PTY session.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "string",
                            "description": "The session ID",
                        },
                        "lines": {
                            "type": "integer",
                            "description": "Number of lines to return from end of buffer. Omit for full buffer.",
                        },
                    },
                    "required": ["session_id"],
                },
            ),
            Tool(
                name="stop_session",
                description="Stop and clean up a PTY session.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "string",
                            "description": "The session ID to stop",
                        },
                    },
                    "required": ["session_id"],
                },
            ),
            Tool(
                name="set_sentinel",
                description="Change the sentinel command for a session. Use when switching between shells/REPLs (e.g., from bash to python).",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "string",
                            "description": "The session ID",
                        },
                        "sentinel_command": {
                            "type": "string",
                            "description": "New sentinel command template. Use {sentinel} placeholder. Examples: 'echo {sentinel}' (bash), \"print('{sentinel}')\" (python)",
                        },
                    },
                    "required": ["session_id", "sentinel_command"],
                },
            ),
            Tool(
                name="list_sessions",
                description="List all active PTY sessions.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        try:
            if name == "start_session":
                return await _start_session(session_manager, arguments)
            elif name == "run_command":
                return await _run_command(session_manager, arguments)
            elif name == "send_keys":
                return await _send_keys(session_manager, arguments)
            elif name == "get_buffer":
                return await _get_buffer(session_manager, arguments)
            elif name == "stop_session":
                return await _stop_session(session_manager, arguments)
            elif name == "set_sentinel":
                return await _set_sentinel(session_manager, arguments)
            elif name == "list_sessions":
                return await _list_sessions(session_manager)
            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]


async def _start_session(
    manager: SessionManager, args: dict
) -> list[TextContent]:
    config = SessionConfig(
        shell=args.get("shell", SessionConfig().shell),
        cwd=args.get("cwd", SessionConfig().cwd),
        timeout_seconds=args.get("timeout_seconds", 1800),
        buffer_size=args.get("buffer_size", 1000),
        sentinel_command=args.get("sentinel_command", "echo {sentinel}"),
    )

    session = await manager.create_session(config)

    return [
        TextContent(
            type="text",
            text=f"Session started: {session.session_id}\nShell: {config.shell}\nCWD: {config.cwd}",
        )
    ]


async def _run_command(
    manager: SessionManager, args: dict
) -> list[TextContent]:
    session_id = args["session_id"]
    command = args["command"]
    timeout = args.get("timeout", 30.0)

    session = manager.get_session(session_id)
    if not session:
        return [TextContent(type="text", text=f"Session not found: {session_id}")]

    output, completed = await session.run_command(command, timeout)

    if completed:
        return [TextContent(type="text", text=output)]
    else:
        return [
            TextContent(
                type="text",
                text=f"[TIMEOUT: Command did not complete within {timeout}s]\n{output}",
            )
        ]


async def _send_keys(
    manager: SessionManager, args: dict
) -> list[TextContent]:
    session_id = args["session_id"]
    keys = args["keys"]

    session = manager.get_session(session_id)
    if not session:
        return [TextContent(type="text", text=f"Session not found: {session_id}")]

    # Process escape sequences
    keys = keys.encode().decode("unicode_escape")

    await session.send_keys(keys)

    return [TextContent(type="text", text="Keys sent")]


async def _get_buffer(
    manager: SessionManager, args: dict
) -> list[TextContent]:
    session_id = args["session_id"]
    lines = args.get("lines")

    session = manager.get_session(session_id)
    if not session:
        return [TextContent(type="text", text=f"Session not found: {session_id}")]

    buffer = session.get_buffer(lines)

    return [TextContent(type="text", text=buffer)]


async def _stop_session(
    manager: SessionManager, args: dict
) -> list[TextContent]:
    session_id = args["session_id"]

    removed = await manager.remove_session(session_id)

    if removed:
        return [TextContent(type="text", text=f"Session stopped: {session_id}")]
    else:
        return [TextContent(type="text", text=f"Session not found: {session_id}")]


async def _set_sentinel(
    manager: SessionManager, args: dict
) -> list[TextContent]:
    session_id = args["session_id"]
    sentinel_command = args["sentinel_command"]

    session = manager.get_session(session_id)
    if not session:
        return [TextContent(type="text", text=f"Session not found: {session_id}")]

    session.config.sentinel_command = sentinel_command

    return [
        TextContent(
            type="text",
            text=f"Sentinel command updated to: {sentinel_command}",
        )
    ]


async def _list_sessions(manager: SessionManager) -> list[TextContent]:
    sessions = manager.list_sessions()

    if not sessions:
        return [TextContent(type="text", text="No active sessions")]

    lines = ["Active sessions:"]
    for s in sessions:
        lines.append(
            f"  {s['session_id']}: {s['shell']} (cwd: {s['cwd']}, alive: {s['is_alive']})"
        )

    return [TextContent(type="text", text="\n".join(lines))]
