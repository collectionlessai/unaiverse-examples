import os
from unaiverse.agent import Agent
from unaiverse.dataprops import Data4Proc
from unaiverse.modules.networks import SiteRAG
from unaiverse.networking.node.node import Node
from unaiverse.utils.misc import save_node_addresses_to_file

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

# TODO replace node_id="..." with node_name="SiteRAG"
# TODO replace password with unaiverse key
# Node hosting agent
node_agent = Node(node_id="2bdcbf6376094d75b15d937a045ebad9", hidden=True,
                  unaiverse_key="password", hosted=agent, clock_delta=1. / 10.)

# Dumping public addresses to file
save_node_addresses_to_file(node_agent, os.path.dirname(__file__), public=True)

# Running node
node_agent.run()
