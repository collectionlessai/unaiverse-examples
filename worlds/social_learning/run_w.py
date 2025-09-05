import os
from src.world import WWorld
from unaiverse.networking.node.node import Node
from unaiverse.utils.misc import save_node_addresses_to_file

# world
world = WWorld()

# node hosting world
node = Node(node_id="820c68076ee34efe99d02ea0b2de325c",
            unaiverse_key="password", hosted=world, clock_delta=1. / 10.,
            world_masters_node_ids=["f1abec9edbff432f9b0cf6d6ce898a50"])

# dumping world addresses to file
save_node_addresses_to_file(node, os.path.dirname(__file__), public=True)

# running node
node.run()
