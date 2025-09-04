import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from unaiverse.agent import Agent
from unaiverse.dataprops import Data4Proc
from unaiverse.networking.node.node import Node
from unaiverse.library.modules.networks import SmolVLM
from unaiverse.utils.misc import save_node_addresses_to_file

# our agent
agent = Agent(proc=SmolVLM(),
              proc_inputs=[Data4Proc(data_type="img", pubsub=False, private_only=False),
                           Data4Proc(data_type="text", pubsub=False, private_only=False)],
              proc_outputs=[Data4Proc(data_type="text", pubsub=False, private_only=False)],
              proc_opts={})

# node hosting our agent
node_agent = Node(node_id="f3a6023bb69443088f8bc80b0fbe6ed6",
                  password="password", hosted=agent, clock_delta=1. / 10.)

# dumping public addresses to file
save_node_addresses_to_file(node_agent, os.path.dirname(__file__), public=True)

# running node
node_agent.run()
