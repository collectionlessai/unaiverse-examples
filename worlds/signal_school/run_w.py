import os
from src.world import WWorld
from unaiverse.networking.node.node import Node
from unaiverse.utils.misc import save_node_addresses_to_file

# world "Signal School"
world = WWorld()

# node hosting world "Signal School"
node = Node(node_id="1ccfcb72165047b28b7f28239bf5e5c7",
            unaiverse_key="password", hosted=world, clock_delta=1. / 1000.,
            world_masters_node_ids=["c3aa541d54964852b3f96198920ef508"])

# dumping world addresses to file
save_node_addresses_to_file(node, os.path.dirname(__file__), public=False)

# running node
node.run()
