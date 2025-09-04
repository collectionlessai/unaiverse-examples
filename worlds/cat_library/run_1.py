import os
from unaiverse.agent import Agent
from unaiverse.networking.node.node import Node
from unaiverse.utils.misc import get_node_addresses_from_file

# agent "Alice" (teacher)
agent = Agent(proc=None, buffer_generated_by_others="all")

# node hosting agent "Alice"
node = Node(node_id="8be9a260e7ee4c1d92d3ca3579f9bac1",
            password="password", hosted=agent, clock_delta=1. / 10.)

# telling "Alice" to join world
node.ask_to_join_world(addresses=get_node_addresses_from_file(os.path.dirname(__file__)))

# running node
node.run()
