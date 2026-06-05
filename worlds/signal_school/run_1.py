from unaiverse.agent import Agent
from unaiverse.networking.node.node import Node

# Agent (teacher)
agent = Agent(proc=None, buffer_generated_by_others="all", merge_flat_stream_labels=True)

# Node hosting agent
node = Node(node_name="Test1", hosted=agent, hidden=True, clock_delta=1. / 100.)

# Running node
node.run(join_world="SignalSchool")
