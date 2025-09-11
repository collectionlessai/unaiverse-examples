import os
from unaiverse.agent import Agent
from unaiverse.dataprops import Data4Proc
from unaiverse.modules.networks import Phi
from unaiverse.networking.node.node import Node
from unaiverse.utils.misc import get_node_addresses_from_file

# Agent
agent = Agent(proc=Phi(),
              proc_inputs=[Data4Proc(data_type="text", pubsub=False, private_only=False)],
              proc_outputs=[Data4Proc(data_type="text", pubsub=False, private_only=False)],
              proc_opts={})

# Node hosting agent
node = Node(node_name="ChatAI", hosted=agent, hidden=True, clock_delta=1. / 10.)

# Telling agent to join world
node.ask_to_join_world(node_name="ChatRoom")

# Running node
node.run()
