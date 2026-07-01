"""Football KG MCP Server — auto-generated via samyama-mcp-serve.

Usage:
    # Embedded mode (loads demo data on startup):
    python -m mcp_server.server --max-tournaments 5

    # Connect to running Samyama server with pre-loaded data:
    python -m mcp_server.server --url http://localhost:8080

    # List all auto-generated + custom tools:
    python -m mcp_server.server --max-tournaments 5 --list-tools

    # Claude Desktop config (embedded with 5 tournaments):
    # {"mcpServers": {"football-kg": {
    #     "command": "python", "args": ["-m", "mcp_server.server", "--max-tournaments", "5"]}}}
"""

from __future__ import annotations

import argparse
import os
import sys


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="football-kg-mcp",
        description="Football Knowledge Graph MCP Server (powered by samyama-mcp-serve)",
    )
    parser.add_argument(
        "--url",
        default=None,
        help="Connect to a running Samyama server (skip embedded loading).",
    )
    parser.add_argument(
        "--max-tournaments",
        type=int,
        default=5,
        help="Number of tournaments to load in embedded mode (default: 5, 0 = all).",
    )
    parser.add_argument(
        "--data-dir",
        default="data",
        help="Path to World Cup CSV files (default: data).",
    )
    parser.add_argument(
        "--list-tools",
        action="store_true",
        help="Print discovered tools and exit.",
    )
    parser.add_argument(
        "--name",
        default="Football KG",
        help="MCP server name.",
    )

    args = parser.parse_args(argv)

    from samyama import SamyamaClient

    if args.url:
        client = SamyamaClient.connect(args.url)
    else:
        client = SamyamaClient.embedded()
        _load_data(client, args.data_dir, args.max_tournaments)

    # Resolve config path relative to this file
    config_path = os.path.join(os.path.dirname(__file__), "config.yaml")

    from samyama_mcp.config import ToolConfig
    from samyama_mcp.server import SamyamaMCPServer

    config = ToolConfig.from_yaml(config_path)
    server = SamyamaMCPServer(
        client, server_name=args.name, config=config
    )

    if args.list_tools:
        tools = server.list_tools()
        print(f"Football KG: {len(tools)} tools\n")
        for name in sorted(tools):
            print(f"  - {name}")
        sys.exit(0)

    server.run()


def _load_data(client, data_dir: str, max_tournaments: int) -> None:
    """Load football data from DataHub World Cup CSV files."""
    if not os.path.isdir(data_dir):
        print(
            f"Warning: data directory '{data_dir}' not found. "
            f"Starting with empty graph.",
            file=sys.stderr,
        )
        return

    from etl.loader import load_football

    stats = load_football(client, data_dir=data_dir, max_tournaments=max_tournaments)
    print(
        f"Loaded {stats.get('matches', 0)} matches "
        f"({stats.get('nodes', 0)} nodes)",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
