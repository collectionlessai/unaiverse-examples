from unaiverse.agent import Agent
from unaiverse.modules.networks import Phi
from unaiverse.networking.node.node import Node

# Agent
agent = Agent(proc=Phi(), proc_inputs=["text"], proc_outputs=["text"])

# Node hosting agent
node = Node(agent, node_name="Expert", hidden=True, clock_delta=1. / 20.)

# Running node
node.run(join_world="CompanyBrain")
