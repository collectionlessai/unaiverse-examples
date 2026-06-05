from unaiverse.agent import Agent
from unaiverse.modules.networks import SmolVLM
from unaiverse.networking.node.node import Node

# Agent
agent = Agent(proc=SmolVLM(), proc_inputs=["img", "text"], proc_outputs=["text"])

# Node hosting agent
node = Node(agent, node_name="SmolVLM", hidden=True, clock_delta=1. / 20.)

# Running node
node.run(join_world="InfoExtraction")
