import os
import json
import torch
import asyncio
import threading

# Unaiverse imports
from unaiverse.agent import Agent
from unaiverse.dataprops import Data4Proc
from unaiverse.networking.node.node import Node


# --------- Code from the a2a_mcp/mcp/client.py file ---------
# MCP related imports
from contextlib import asynccontextmanager
from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client
from mcp.types import CallToolResult

@asynccontextmanager
async def init_session(host, port, transport):
    """Initializes and manages an MCP ClientSession based on the specified transport.

    This asynchronous context manager establishes a connection to an MCP server
    using either Server-Sent Events (SSE) or Standard I/O (STDIO) transport.
    It handles the setup and teardown of the connection and yields an active
    `ClientSession` object ready for communication.

    Args:
        host: The hostname or IP address of the MCP server (used for SSE).
        port: The port number of the MCP server (used for SSE).
        transport: The communication transport to use ('sse' or 'stdio').

    Yields:
        ClientSession: An initialized and ready-to-use MCP client session.

    Raises:
        ValueError: If an unsupported transport type is provided (implicitly,
                    as it won't match 'sse' or 'stdio').
        Exception: Other potential exceptions during client initialization or
                   session setup.
    """
    if transport == 'sse':
        url = f'http://{host}:{port}/sse'
        async with sse_client(url) as (read_stream, write_stream):
            async with ClientSession(
                read_stream=read_stream, write_stream=write_stream
            ) as session:
                await session.initialize()
                print('SSE ClientSession initialized successfully.')
                yield session
    elif transport == 'stdio':
        if not os.getenv('GOOGLE_API_KEY'):
            raise ValueError('GOOGLE_API_KEY is not set')
        stdio_params = StdioServerParameters(
            command='uv',
            args=['run', 'a2a-mcp'],
            env=os.getenv('GOOGLE_API_KEY'),
        )
        async with stdio_client(stdio_params) as (read_stream, write_stream):
            async with ClientSession(
                read_stream=read_stream,
                write_stream=write_stream,
            ) as session:
                await session.initialize()
                print('STDIO ClientSession initialized successfully.')
                yield session
    else:
        print(f'Unsupported transport type: {transport}')
        raise ValueError(
            f"Unsupported transport type: {transport}. Must be 'sse' or 'stdio'."
        )


async def find_agent(session: ClientSession, query) -> CallToolResult:
    """Calls the 'find_agent' tool on the connected MCP server.

    Args:
        session: The active ClientSession.
        query: The natural language query to send to the 'find_agent' tool.

    Returns:
        The result of the tool call.
    """
    print(f"Calling 'find_agent' tool with query: '{query[:50]}...'")
    return await session.call_tool(
        name='find_agent',
        arguments={
            'query': query,
        },
    )
# --------- End code from the a2a_mcp/mcp/client.py file ---------


class A2AMCPFinder(torch.nn.Module):
    def __init__(self, config: dict):
        """
        config (dict):
            {
                "host": "localhost",
                "port": 10100,
                "tool_name": "find_agent",
                "arg_key": "query" # the name of the argument expected from the tool
            }
        """
        super(A2AMCPFinder, self).__init__()
        self.config = config

    def forward(self, msg: str, first: bool = False, last: bool = False):
        """
        Forwards the 'msg' to the A2A server in a separate thread to avoid
        asyncio loop conflicts.
        """
        result = {"output": None, "error": None}

        def run_in_thread():
            try:
                result["output"] = asyncio.run(self._run_mcp_tool(msg))
            except Exception as e:
                result["error"] = str(e)

        # Spin up a thread to handle the async I/O
        t = threading.Thread(target=run_in_thread)
        t.start()
        t.join()

        if result["error"]:
            return f"Error querying 'MCP': {result['error']}"
        return result["output"]

    def _format_markdown_card(self, json_str: str) -> str:
        """
        Used to format the agent card JSON into a nice Markdown representation.
        """
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            return json_str

        # Build the Markdown
        md_lines = []
        
        # Header
        name = data.get("name", "Unknown Agent")
        version = data.get("version", "v?.?.?")
        md_lines.append(f"### 🤖 {name} <span style='color:gray; font-size:0.8em'>v{version}</span>")
        
        # Description
        desc = data.get("description", "")
        if desc:
            md_lines.append(f"_{desc}_")
        
        # Skills
        skills = data.get("skills", [])
        if skills:
            md_lines.append("\n#### 🛠️ Skills:")
            for skill in skills:
                s_name = skill.get("name", "Unnamed Skill")
                s_desc = skill.get("description", "")
                md_lines.append(f"- **{s_name}**: {s_desc}\n")
                
                # Examples
                examples = skill.get("examples", [])
                if examples:
                    md_lines.append(f"  > *E.g.: \"{examples[0]}\"*")

        return "\n".join(md_lines)
    
    async def _run_mcp_tool(self, user_input: str) -> str:
        """
        Connects to the MCP server and uses a chosen tool.
        """
        host = self.config.get("host", "localhost")
        port = self.config.get("port")
        tool_name = self.config.get("tool_name")
        arg_key = self.config.get("arg_key", "query")
        print(f"Connecting to the MCP server {host}:{port} to use '{tool_name}'")
        
        try:
            # Uses context manager from a2a_mcp/mcp/client.py
            async with init_session(host, port, 'sse') as session:
                arguments = {arg_key: user_input}
                
                # Calls the tool defined in a2a_mcp/mcp/client.py
                result = await session.call_tool(name=tool_name, arguments=arguments)
                
                # Extract the content from the result
                if result.content and len(result.content) > 0:
                    text_response = result.content[0].text
                    return self._format_markdown_card(text_response)
                else:
                    return "No agent found."

        except Exception as e:
            print(f"Error during the MCP request: {e}")
            raise e

if __name__ == "__main__":

    # Config to call an MCP tool
    mcp_config = {
        "host": "localhost",
        "port": 10100,
        "tool_name": "find_agent",
        "arg_key": "query"
    }

    agent = Agent(
        proc=A2AMCPFinder(config=mcp_config),
        proc_inputs=[Data4Proc(data_type="text", pubsub=False, private_only=False)],
        proc_outputs=[Data4Proc(data_type="text", pubsub=False, private_only=False)],
        proc_opts={}
    )

    node_agent = Node(
        node_name="A2AMCPFinder", 
        hosted=agent, 
        hidden=True, 
        clock_delta=1. / 10.,
        save_checkpoint_every=-1.
    )

    # Ensure you started the A2A MCP server separately before running this!
    node_agent.run()
