import json
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from devsec_bench.models import TOOLS


async def test_real_mcp_stdio_protocol():
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "devsec_bench.tools.mcp_server", "--scenario", "SEC-001"],
    )
    async with (
        stdio_client(parameters) as (reader, writer),
        ClientSession(reader, writer) as session,
    ):
        await session.initialize()
        tools = await session.list_tools()
        assert {tool.name for tool in tools.tools} == TOOLS
        for tool in tools.tools:
            assert tool.inputSchema["type"] == "object"
            assert tool.outputSchema is not None
        listing = await session.call_tool("list_files", {})
        assert "app.py" in listing.content[0].text
        read = await session.call_tool("read_file", {"path": "app.py"})
        assert "SYNTHETIC_DEMO_ONLY" in read.content[0].text
        denied = await session.call_tool("read_file", {"path": "../scenario.yaml"})
        assert "error" in json.loads(denied.content[0].text)
        unauthorized = await session.call_tool("list_files", {"repository": "host"})
        assert "error" in unauthorized.content[0].text
