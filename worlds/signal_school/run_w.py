from src.world import WWorld
from unaiverse.networking.node.node import Node

# World
world = WWorld()

# Node hosting world
node = Node(world, node_name="TestWorld0", hidden=True, clock_delta=1. / 100.,
            world_masters_node_names=["Test1"])

# Running node
node.run()
