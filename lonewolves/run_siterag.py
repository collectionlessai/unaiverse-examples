from unaiverse.agent import Agent
from unaiverse.dataprops import Data4Proc
from unaiverse.modules.networks import SiteRAG
from unaiverse.networking.node.node import Node

"""
Dependencies:
Use a specific version of "transformers", otherwise "sentence-transformers" will complain.

pip install transformers==4.49.0 sentence-transformers langchain chromadb beautifulsoup4 requests
pip install tiktoken blobfile langchain-community
pip install --no-cache-dir --force-reinstall sentencepiece
"""

# Agent
agent = Agent(proc=SiteRAG(site_url="https://collectionless.ai/"),
              proc_inputs=[Data4Proc(data_type="text", pubsub=False, private_only=False)],
              proc_outputs=[Data4Proc(data_type="text", pubsub=False, private_only=False)],
              proc_opts={})

# Node hosting agent
node_agent = Node(node_name="SiteRAG", hosted=agent, hidden=True, clock_delta=1. / 10.)

# Running node
node_agent.run()
