import os
from src.world import WWorld
from unaiverse.networking.node.node import Node
from unaiverse.utils.misc import save_node_addresses_to_file

# World "Cat Library"
world = WWorld()

# Node hosting world "Cat Library"
node = Node(node_id="2c13e98c752444689038a32a962c3979",
            unaiverse_key="password", hosted=world, clock_delta=1. / 10.,
            world_masters_node_ids=["8be9a260e7ee4c1d92d3ca3579f9bac1"])

# Dumping world addresses to file
save_node_addresses_to_file(node, os.path.dirname(__file__), public=False)

# Running node
node.run()
