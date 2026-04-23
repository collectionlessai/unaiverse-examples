from src.world import WWorld
from unaiverse.networking.node.node import Node

# World
world = WWorld()

# Node hosting world
node = Node(node_name="_TuringHotel", hosted=world, hidden=False, clock_delta=1./10.)

# Running node
node.run()
