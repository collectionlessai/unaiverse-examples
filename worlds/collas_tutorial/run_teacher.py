from unaiverse.agent import Agent
from unaiverse.networking.node.node import Node

# Agent
agent = Agent(proc=None, buffer_generated_by_others="one")

# Node hosting the teacher agent
node = Node(node_name="CoLLAsTeacher", hosted=agent, hidden=True, clock_delta=1./10.)

# Running node
node.run(join_world="CoLLAsTutorial")
