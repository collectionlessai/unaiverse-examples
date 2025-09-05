import os
from unaiverse.agent import Agent
from unaiverse.networking.node.node import Node
from unaiverse.utils.misc import get_node_addresses_from_file

# agent "Alice" (teacher)
agent = Agent(proc=None, buffer_generated_by_others="all", merge_flat_stream_labels=True)

# node hosting agent "Alice"
node = Node(node_id="c3aa541d54964852b3f96198920ef508",
            unaiverse_key="password", hosted=agent, clock_delta=1. / 1000.)

# telling "Alice" to join world
node.ask_to_join_world(addresses=get_node_addresses_from_file(os.path.dirname(__file__)))

# running node
node.run()
