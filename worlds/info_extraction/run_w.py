import os
from src.world import WWorld
from unaiverse.networking.node.node import Node
from unaiverse.utils.misc import save_node_addresses_to_file


# world
world = WWorld()

# node hosting world
node = Node(node_id="ce50cae6046141d6bfa0da6347a9c686",
            unaiverse_key="password", hosted=world, clock_delta=1. / 10.)

# dumping world addresses to file
save_node_addresses_to_file(node, os.path.dirname(__file__), public=True)

# running node
node.run()
