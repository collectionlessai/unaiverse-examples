from src.world import WWorld
from unaiverse.networking.node.node import Node

# World
world = WWorld()
# world.debug_stats_dashboard()

# Node hosting world
node = Node(node_name="InfoExtraction", hidden=True, hosted=world, clock_delta=1. / 10.)

# Running node
node.run()
