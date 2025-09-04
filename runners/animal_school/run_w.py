import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from unaiverse.networking.node.node import Node
from unaiverse.utils.misc import save_node_addresses_to_file
from unaiverse.library.worlds.animal_school.world import WWorld

# world "School of Animals"
world = WWorld(merge_flat_stream_labels=True)

# node hosting world "Animal Lectures"
node = Node(node_id="d0d5e11bb9864d0580da6cf1b211dd8a",
            password="password", hosted=world, clock_delta=1. / 1000.,
            world_masters_node_ids=["9f287a3a4e2e466f93aaad5098dbbc76"])

# dumping world addresses to file
save_node_addresses_to_file(node, os.path.dirname(__file__), public=True)

# running node
node.run()
