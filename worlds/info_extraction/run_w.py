import os
from src.world import WWorld
from unaiverse.networking.node.node import Node
from unaiverse.utils.misc import save_node_addresses_to_file

# World
world = WWorld()

# TODO replace node_id="..." with node_name="InfoExtraction"
# TODO replace password with unaiverse key
# Node hosting world
node = Node(node_id="ce50cae6046141d6bfa0da6347a9c686", unaiverse_key="<UNAIVERSE_KEY_GOES_HERE>", hidden=True,
            hosted=world, clock_delta=1. / 10.)

# Dumping world addresses to file
save_node_addresses_to_file(node, os.path.dirname(__file__), public=True)

# Running node
node.run()
