import os
from unaiverse.agent import Agent
from unaiverse.dataprops import Data4Proc
from unaiverse.networking.node.node import Node
from unaiverse.utils.misc import get_node_addresses_from_file

# Agent
agent = Agent(proc=None,
              proc_inputs=[Data4Proc(data_type="text", pubsub=False, private_only=True)],
              proc_outputs=[Data4Proc(data_type="text", pubsub=False, private_only=True)])  # Also switch to pubsub=True

# TODO replace node_id="..." with node_name="Broadcaster"
# TODO replace password with unaiverse key
# node hosting agent
node = Node(node_id="255b2dbf73134e18877365d4b9323f46",
            unaiverse_key="password", hosted=agent, clock_delta=1. / 10.)

# Telling agent to join world
node.ask_to_join_world(addresses=get_node_addresses_from_file(os.path.dirname(__file__)))

# Running node
node.run()
