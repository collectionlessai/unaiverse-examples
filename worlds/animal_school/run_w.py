import os
from src.world import WWorld
from unaiverse.networking.node.node import Node
from unaiverse.utils.misc import save_node_addresses_to_file

# world
world = WWorld(merge_flat_stream_labels=True)

# TODO replace node_id="..." with node_name="Test0"
# TODO replace password with unaiverse key
# TODO replace with world_masters_node_ids=["..."] with world_masters_node_names=["Test1"]
# node hosting world
node = Node(node_id="d0d5e11bb9864d0580da6cf1b211dd8a",
            unaiverse_key="password", hosted=world, clock_delta=1. / 1000.,
            world_masters_node_ids=["9f287a3a4e2e466f93aaad5098dbbc76"])

# dumping world addresses to file
save_node_addresses_to_file(node, os.path.dirname(__file__), public=True)

# running node
node.run()
