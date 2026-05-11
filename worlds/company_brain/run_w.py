from src.world import WWorld
from unaiverse.networking.node.node import Node

# World
world = WWorld()

# Node hosting world
node = Node(world, node_name="CompanyBrain", hidden=True, clock_delta=1. / 20.,
            world_masters_node_names=["Dispatcher"])

# Running node
node.run()
