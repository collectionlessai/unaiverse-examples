import os
from unaiverse.agent import Agent
from unaiverse.networking.node.node import Node
from unaiverse.utils.misc import get_node_addresses_from_file

# Agent (teacher)
agent = Agent(proc=None, buffer_generated_by_others="one")

# Node agent
node = Node(node_id="f1abec9edbff432f9b0cf6d6ce898a50",
            unaiverse_key="password", hosted=agent, clock_delta=1. / 10.)

# Telling agent to join world
node.ask_to_join_world(addresses=get_node_addresses_from_file(os.path.dirname(__file__)))

# Running node
node.run()
