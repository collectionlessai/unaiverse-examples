import os
from unaiverse.agent import Agent
from unaiverse.networking.node.node import Node
from unaiverse.utils.misc import get_node_addresses_from_file

# agent
agent = Agent(proc=None, buffer_generated_by_others="all")

# TODO replace node_id="..." with node_name="Test1"
# TODO replace password with unaiverse key
# node hosting agent
node = Node(node_id="9f287a3a4e2e466f93aaad5098dbbc76",
            unaiverse_key="password", hosted=agent, clock_delta=1. / 1000.)

# telling agent to join world
node.ask_to_join_world(addresses=get_node_addresses_from_file(os.path.dirname(__file__)))

# running node
node.run()
