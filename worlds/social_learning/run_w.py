from src.world import WWorld
from unaiverse.networking.node.node import Node

# World
world = WWorld()
# world.debug_stats_dashboard()

# Node hosting world
node = Node(world, node_name="DigitSocialLearning", hidden=True, clock_delta=1. / 15.,
            world_masters_node_names=["DigitClassifier1"])

# Running node
node.run()
