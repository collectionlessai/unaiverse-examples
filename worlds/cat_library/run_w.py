from src.world import WWorld
from unaiverse.networking.node.node import Node

# World
world = WWorld()
# world.debug_stats_dashboard()

# Node hosting world
node = Node(node_name="Test0", hosted=world, hidden=True, clock_delta=1. / 10.,
            world_masters_node_names=["Test1"])

# Running node
node.run()
