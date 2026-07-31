from src.world import WWorld
from unaiverse.networking.node.node import Node

# World
world = WWorld()

# Node hosting world
node = Node(node_name="Hotel delle Imitazioni", hosted=world, hidden=True, clock_delta=1./50.)

# Running node
node.run(show_senders=False)
