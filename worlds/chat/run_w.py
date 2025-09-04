import os
from src.world import WWorld
from unaiverse.networking.node.node import Node
from unaiverse.utils.misc import save_node_addresses_to_file

# world "Chat"
world = WWorld()

# node hosting world "Chat"
node = Node(node_id="72ae13520d3c4043b3de056f47b2baa7",  # "e5fe4a69dd984057ab01c65e2a470881"
            password="password", hosted=world, clock_delta=1. / 10.,
            world_masters_node_ids=["255b2dbf73134e18877365d4b9323f46"])  # ["31a6cea30df847caa22579d55ac06f8d"]

# dumping world addresses to file
save_node_addresses_to_file(node, os.path.dirname(__file__), public=True)

# running node
node.run()
