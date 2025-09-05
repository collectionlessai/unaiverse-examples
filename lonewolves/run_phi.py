import os
from unaiverse.agent import Agent
from unaiverse.dataprops import Data4Proc
from unaiverse.modules.networks import Phi
from unaiverse.networking.node.node import Node
from unaiverse.utils.misc import save_node_addresses_to_file

# Our agent
agent = Agent(proc=Phi(),
              proc_inputs=[Data4Proc(data_type="text", pubsub=False, private_only=False)],
              proc_outputs=[Data4Proc(data_type="text", pubsub=False, private_only=False)],
              proc_opts={})

# Node hosting our agent
node_agent = Node(node_id="98bad85baa1e4ee7bbc811551b6cbffd",
                  unaiverse_key="password", hosted=agent, clock_delta=1. / 10.)

# Dumping public addresses to file
save_node_addresses_to_file(node_agent, os.path.dirname(__file__), public=True)

# Running node
node_agent.run()
