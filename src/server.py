from __future__ import annotations

from .services.mcp_provider import mcp
from .helper.config import server_settings


def main() -> None:
    """
    Entry point for the NameSilo MCP server.
    Exposes a streamable HTTP MCP endpoint.
    """
    mcp.settings.host = server_settings.host
    mcp.settings.port = server_settings.port
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
