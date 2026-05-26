from unaiverse.agent import Agent
from unaiverse.networking.node.node import Node
from unaiverse.modules.networks import FeatherlessAPI

# -----------
# Model, Cost
# -----------
# Qwen/Qwen3.6-35B-A3B, 2


# Agent
agent = Agent(proc=FeatherlessAPI(model="Qwen/Qwen3.6-35B-A3B", cost=2), proc_inputs=["text"], proc_outputs=["text"])

# Node hosting agent
node_agent = Node(agent, node_name="Featherless", hidden=True, clock_delta=1. / 10.)

# Running node
node_agent.run()
