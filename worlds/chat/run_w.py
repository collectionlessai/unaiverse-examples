import os
from src.world import WWorld
from unaiverse.networking.node.node import Node
from unaiverse.utils.misc import save_node_addresses_to_file

# World
world = WWorld()

# TODO replace node_id="..." with node_name="ChatRoom"
# TODO replace password with unaiverse key
# TODO replace with world_masters_node_ids=["..."] with world_masters_node_names=["Broadcaster"]
# Node hosting world
node = Node(node_id="72ae13520d3c4043b3de056f47b2baa7", unaiverse_key="<UNAIVERSE_KEY_GOES_HERE>", hidden=True,
            hosted=world, clock_delta=1. / 10.,
            world_masters_node_ids=["255b2dbf73134e18877365d4b9323f46"])

# Dumping world addresses to file
save_node_addresses_to_file(node, os.path.dirname(__file__), public=True)

# Running node
node.run()
