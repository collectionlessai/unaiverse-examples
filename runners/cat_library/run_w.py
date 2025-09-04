import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from unaiverse.networking.node.node import Node
from unaiverse.utils.misc import save_node_addresses_to_file
from unaiverse.library.worlds.cat_library.world import WWorld

# world "Cat Library"
world = WWorld()

# node hosting world "Cat Library"
node = Node(node_id="2c13e98c752444689038a32a962c3979",
            password="password", hosted=world, clock_delta=1. / 10.,
            world_masters_node_ids=["8be9a260e7ee4c1d92d3ca3579f9bac1"])

# dumping world addresses to file
save_node_addresses_to_file(node, os.path.dirname(__file__), public=False)

# running node
node.run()
