from src.world import WWorld
from unaiverse.networking.node.node import Node

# World
world = WWorld()
# world.debug_stats_dashboard()

# Node hosting world
node = Node(node_name="Class Incremental World", hosted=world, hidden=True, clock_delta=1./10.,
            world_masters_node_names=["CastelldefelsTeacher"])

# Running node
node.run()
