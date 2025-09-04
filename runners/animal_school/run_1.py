import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from unaiverse.agent import Agent
from unaiverse.networking.node.node import Node
from unaiverse.utils.misc import get_node_addresses_from_file

# agent "Alice" (teacher)
agent = Agent(proc=None, buffer_generated_by_others="all")

# node hosting agent "Alice" (teacher)
node = Node(node_id="9f287a3a4e2e466f93aaad5098dbbc76",
            password="password", hosted=agent, clock_delta=1. / 1000.)

# telling "Alice" to join world
node.ask_to_join_world(addresses=get_node_addresses_from_file(os.path.dirname(__file__)))

# running node
node.run()
