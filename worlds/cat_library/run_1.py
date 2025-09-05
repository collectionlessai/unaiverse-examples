import os
from unaiverse.agent import Agent
from unaiverse.networking.node.node import Node
from unaiverse.utils.misc import get_node_addresses_from_file

# Agent "Alice" (teacher)
agent = Agent(proc=None, buffer_generated_by_others="all")

# Node hosting agent
node = Node(node_id="8be9a260e7ee4c1d92d3ca3579f9bac1",
            unaiverse_key="password", hosted=agent, clock_delta=1. / 10.)

# Telling "Alice" to join world
node.ask_to_join_world(addresses=get_node_addresses_from_file(os.path.dirname(__file__)))

# Running node
node.run()
