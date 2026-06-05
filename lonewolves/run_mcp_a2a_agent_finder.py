import os
import json
import torch
import asyncio
import threading
from unaiverse.agent import Agent
from unaiverse.networking.node.node import Node

# --------- Code from the src/a2a_mcp/a2a_mcp/mcp/client.py file ---------
# DISCLAIMER & ATTRIBUTION:
# The following section (`init_session` / `find_agent` functions as well as their imports)
# is adapted from the 'a2a-samples' GitHub repository (Apache 2.0 License).
# This code acts as a specific client implementation to communicate with their
# Model Context Protocol (MCP) server implemented in the a2a_mcp example for python.
# It is NOT a generic A2A wrapper, but a specific bridge for this example.
# Please refer to the original repository for more details:
#   https://github.com/a2aproject/a2a-samples/tree/main/samples/python/agents/a2a_mcp

# MCP related imports
from contextlib import asynccontextmanager
from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client
from mcp.types import CallToolResult


@asynccontextmanager
async def init_session(host, port, transport):
    """Initializes and manages an MCP ClientSession based on the specified transport.
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
    """
    We inherit from torch.nn.Module because the Unaiverse `Agent` class expects
    a callable module as its processor ('proc'). This class acts as a proxy node:
    it receives a message from the Unaiverse network, forwards it to the external
    MCP server, and returns the formatted result.
    
    This is a "Proxy Node". It does not perform the logic itself but forwards the request
    to an external entity (in this case the MCP Server) and returns the result to the network.
    """
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

    def forward(self, msg: str):
        """
        The entry point when this Node receives a message.
        
        Crucially, we spin up a separate thread here. The Unaiverse node loop
        might interfere with the asyncio loop required by the MCP client.
        To ensure stability, we isolate the async I/O of the MCP request 
        in its own thread using `asyncio.run()`.
        """
        result: dict[str, None | str] = {"output": None, "error": None}

        def run_in_thread():
            try:
                # We block this thread until the async MCP call is finished.
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

    @staticmethod
    def _format_markdown_card(json_str: str) -> str:
        """
        The raw response from the A2A agent is a JSON string. 
        We parse it here to make it readable for the end user in our UI.
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
        This is where the actual bridge happens. We use the 'init_session' context
        manager (from the a2a-samples repo) to establish the SSE connection,
        and then we invoke the tool specified in our config.
        """
        host = self.config.get("host", "localhost")
        port = self.config.get("port")
        tool_name = self.config.get("tool_name")
        arg_key = self.config.get("arg_key", "query")
        print(f"Connecting to the MCP server {host}:{port} to use '{tool_name}'")
        
        try:
            # Uses context manager from a2a_mcp/mcp/client.py
            # We assume 'sse' transport here as it is standard for network agents.
            async with init_session(host, port, 'sse') as session:
                arguments = {arg_key: user_input}
                
                # Calls the tool defined in a2a_mcp/mcp/client.py
                result = await session.call_tool(name=tool_name, arguments=arguments)
                
                # Extract the content from the result
                if result.content and len(result.content) > 0:
                    text_response = result.content[0].text
                    return A2AMCPFinder._format_markdown_card(text_response)
                else:
                    return "No agent found."

        except Exception as e:
            print(f"Error during the MCP request: {e}")
            raise e


if __name__ == "__main__":

    # ==================================================================================
    # HOW TO RUN THIS EXAMPLE
    # ==================================================================================
    # This script assumes you are running the 'a2a-samples' MCP server locally.
    # The 'a2a-samples' repo serves as a registry of agent cards (Travel, Hotel, etc.).
    #
    # PREREQUISITES:
    # 1. You must have the `a2a-samples` repository cloned locally.
    #    Repo: https://github.com/a2aproject/a2a-samples
    # 2. You must have `uv` installed (python package manager used in the sample).
    # 3. You must have a Google API Key if using the GenAI features of the sample, 
    #    though for simple discovery, it might not be strictly required depending on implementation.
    #
    # SETUP INSTRUCTIONS (Terminal 1 - The MCP Server):
    # Navigate to the a2a sample directory:
    #   cd samples/python/agents/a2a_mcp
    #
    # Create the virtual environment:
    #   uv venv
    #   source .venv/bin/activate
    #
    # Run the MCP Server (Hosting the Agent Cards):
    #   uv run --env-file .env a2a-mcp --run mcp-server --transport sse
    #
    #   * Note: This defaults to port 10100, which matches our config below.
    #
    # EXECUTION (Terminal 2 - This Unaiverse Node):
    # Once the server in Terminal 1 is running and listening on port 10100,
    # you can run this script. It will spin up a Unaiverse Node that acts as a 
    # client to that server.
    #
    #   python run_mcp_a2a_agent_finder.py
    # ==================================================================================

    # Config to call the 'find_agent' tool on the local MCP server
    mcp_config = {
        "host": "localhost",
        "port": 10100,
        "tool_name": "find_agent",
        "arg_key": "query"
    }

    # We wrap our custom Torch module (A2AMCPFinder) into a UNaIVERSE Agent
    agent = Agent(
        proc=A2AMCPFinder(config=mcp_config),
        proc_inputs=["text"],
        proc_outputs=["text"]
    )

    # Finally, we host the Agent in a Node, making it a participant in the network.
    node_agent = Node(
        agent,
        node_name="A2AMCPFinder",
        hidden=True,
        clock_delta=1. / 10.,
        save_checkpoint_every=-1.
    )

    # Run the node. 
    # In a real scenario, this node would wait for messages from other nodes (like a UI node).
    # Since this is a standalone test script, ensure your environment sends input 
    # or the node is configured to poll/interact as needed.
    node_agent.run()
