import os
from src.world import WWorld
from unaiverse.networking.node.node import Node
from unaiverse.utils.misc import save_node_addresses_to_file

# World
world = WWorld(merge_flat_stream_labels=True)

# Node hosting world
node = Node(node_name="Test0", unaiverse_key="<UNAIVERSE_KEY_GOES_HERE>",
            hosted=world, clock_delta=1. / 1000.,
            world_masters_node_names=["Test1"])

# Dumping world addresses to file
save_node_addresses_to_file(node, os.path.dirname(__file__), public=True)

# Running node
node.run()
