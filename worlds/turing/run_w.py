from src.world import WWorld
from unaiverse.networking.node.node import Node

# World
world = WWorld()

# Node hosting world
node = Node(node_name="_TuringHotel", hosted=world, hidden=True, clock_delta=1./2.)

# Running node
node.run()
