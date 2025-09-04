import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from unaiverse.networking.node.node import Node
from unaiverse.utils.misc import save_node_addresses_to_file
from unaiverse.library.worlds.info_extraction.world import WWorld

# world
world = WWorld()

# node hosting world
node = Node(node_id="ce50cae6046141d6bfa0da6347a9c686",
            password="password", hosted=world, clock_delta=1. / 10.)

# dumping world addresses to file
save_node_addresses_to_file(node, os.path.dirname(__file__), public=True)

# running node
node.run()
