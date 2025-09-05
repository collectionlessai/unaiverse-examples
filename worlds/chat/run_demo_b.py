import os
from unaiverse.agent import Agent
from unaiverse.dataprops import Data4Proc
from unaiverse.networking.node.node import Node
from unaiverse.utils.misc import get_node_addresses_from_file

# agent
agent = Agent(proc=None,
              proc_inputs=[Data4Proc(data_type="text", pubsub=False, private_only=True)],
              proc_outputs=[Data4Proc(data_type="text", pubsub=False, private_only=True)],
              proc_opts={})

# TODO replace node_id="..." with node_name="PyChatBis"
# TODO replace password with unaiverse key
# node hosting agent
node = Node(node_id="0d8f85ca82d0497bad906c6905fac8d0",
            unaiverse_key="password", hosted=agent, clock_delta=1. / 10.)

# telling agent to join world
node.ask_to_join_world(addresses=get_node_addresses_from_file(os.path.dirname(__file__)))

# running node
node.run(interact_mode_opts={})  # the presence of "interact_mode_opts" tells we want to jump into the interactive mode
