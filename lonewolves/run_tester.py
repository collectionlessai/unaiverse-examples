import os
from unaiverse.agent import Agent
from unaiverse.dataprops import Data4Proc
from unaiverse.networking.node.node import Node
from unaiverse.utils.misc import get_node_addresses_from_file

# Agent
agent = Agent(proc=None,
              proc_inputs=[Data4Proc(data_type="text", pubsub=False, private_only=False)],  # It must be public
              proc_outputs=[Data4Proc(data_type="text", pubsub=False, private_only=False)],  # It must be public
              proc_opts={})

# TODO replace node_id="..." with node_name="Test1"
# TODO replace password with unaiverse key
# Node hosting agent
node_agent = Node(node_id="1b37140a496948df80cc0e8c996e9501",
                  unaiverse_key="password", hosted=agent, clock_delta=1. / 10.)

# Connecting to a lone wolf
wolf_peer_id = node_agent.ask_to_get_in_touch(addresses=get_node_addresses_from_file(os.path.dirname(__file__)))

# Running node
if wolf_peer_id is not None:
    node_agent.run(interact_mode_opts={"lone_wolf_peer_id": wolf_peer_id})
