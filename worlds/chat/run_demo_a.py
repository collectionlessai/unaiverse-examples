import os
from unaiverse.agent import Agent
from unaiverse.dataprops import Data4Proc
from unaiverse.networking.node.node import Node
from unaiverse.utils.misc import get_node_addresses_from_file

# Agent
agent = Agent(proc=None,
              proc_inputs=[Data4Proc(data_type="text", pubsub=False, private_only=True)],
              proc_outputs=[Data4Proc(data_type="text", pubsub=False, private_only=True)],
              proc_opts={})

# TODO replace node_id="..." with node_name="Test0"
# Node hosting agent
node = Node(node_id="3054024a135c4e65b495e8720e775881", unaiverse_key="<UNAIVERSE_KEY_GOES_HERE>", hidden=True,
            hosted=agent, clock_delta=1. / 10.)

# Telling agent to join world
node.ask_to_join_world(addresses=get_node_addresses_from_file(os.path.dirname(__file__)))

# Running node
node.run(interact_mode_opts={})  # The presence of "interact_mode_opts" tells we want to jump into the interactive mode
