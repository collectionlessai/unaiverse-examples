from src.world import WWorld
from unaiverse.networking.node.node import Node

# World
world = WWorld()

# Node hosting world
node = Node(node_name="CatLibrary", hosted=world, hidden=True, clock_delta=1. / 40.,
            world_masters_node_names=["Test1"])

# Running node
node.run()
