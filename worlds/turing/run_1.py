from unaiverse.agent import Agent
from unaiverse.networking.node.node import Node

# Agent
agent = Agent(proc=None)

# Node hosting agent
node = Node(node_name="TuringHotelManager", hosted=agent, hidden=True, clock_delta=1. / 50.)

# Running node
node.run(join_world="TuringHotel")
