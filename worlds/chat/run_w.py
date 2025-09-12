from src.world import WWorld
from unaiverse.networking.node.node import Node

# World
world = WWorld()

# Node hosting world
node = Node(node_name="ChatRoom", hosted=world, hidden=True, clock_delta=1. / 10.,
            world_masters_node_names=["Broadcaster"])

# Running node
node.run()
