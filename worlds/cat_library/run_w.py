import os
from src.world import WWorld
from unaiverse.networking.node.node import Node
from unaiverse.utils.misc import save_node_addresses_to_file

# World
world = WWorld()

# TODO replace node_id="..." with node_name="Test0"
# TODO replace with world_masters_node_ids=["..."] with world_masters_node_names=["Test1"]
# Node hosting world
node = Node(node_id="2c13e98c752444689038a32a962c3979", unaiverse_key="<UNAIVERSE_KEY_GOES_HERE>", hidden=True,
            hosted=world, clock_delta=1. / 10.,
            world_masters_node_ids=["8be9a260e7ee4c1d92d3ca3579f9bac1"])

# Dumping world addresses to file
save_node_addresses_to_file(node, os.path.dirname(__file__), public=False)

# Running node
node.run()
