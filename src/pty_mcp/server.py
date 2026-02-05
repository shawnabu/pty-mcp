"""MCP server for PTY sessions."""

import argparse
import asyncio

from mcp.server import Server
from mcp.server.stdio import stdio_server

from .config import ServerConfig
from .session import SessionManager
from .tools import register_tools


async def run_server(config: ServerConfig) -> None:
    """Run the MCP server."""
    server = Server("pty-mcp")
    session_manager = SessionManager(
        max_sessions=config.max_sessions,
        log_dir=config.log_dir
    )

    await session_manager.start()
    register_tools(server, session_manager)

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )

    await session_manager.stop()


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="MCP server for PTY sessions",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--max-sessions",
        type=int,
        default=10,
        help="Maximum concurrent PTY sessions",
    )
    parser.add_argument(
        "--log-dir",
        type=str,
        default=None,
        help="Directory to write session logs (must exist)",
    )

    args = parser.parse_args()

    config = ServerConfig(
        max_sessions=args.max_sessions,
        log_dir=args.log_dir
    )

    asyncio.run(run_server(config))


if __name__ == "__main__":
    main()
