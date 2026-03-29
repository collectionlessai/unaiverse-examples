from src.world import WWorld
from unaiverse.networking.node.node import Node

# World
world = WWorld()
# world.debug_stats_dashboard()

# Node hosting world
node = Node(node_name="_DigitSocialLearning", hosted=world, hidden=True, clock_delta=1. / 10.,
            world_masters_node_names=["_DigitClassifier1"])

# Running node
node.run()
