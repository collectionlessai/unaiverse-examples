import os
from unaiverse.agent import Agent
from unaiverse.dataprops import Data4Proc
from unaiverse.networking.node.node import Node
from unaiverse.modules.networks import TinyLLama
from unaiverse.utils.misc import save_node_addresses_to_file

# our agent
agent = Agent(proc=TinyLLama(),
              proc_inputs=[Data4Proc(data_type="text", pubsub=False, private_only=False)],
              proc_outputs=[Data4Proc(data_type="text", pubsub=False, private_only=False)],
              proc_opts={})

# node hosting our agent
node_agent = Node(node_id="63a2fecf52b24989bb81ec35a7b8173e",
                  unaiverse_key="password", hosted=agent, clock_delta=1. / 10.)

# dumping public addresses to file
save_node_addresses_to_file(node_agent, os.path.dirname(__file__), public=True)

# running node
node_agent.run()
