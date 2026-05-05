from unaiverse.agent import Agent
from unaiverse.modules.networks import Phi
from unaiverse.networking.node.node import Node

# Agent
agent = Agent(proc=Phi(), proc_inputs=["text"], proc_outputs=["text"])

# Node hosting agent
node_agent = Node(agent, node_name="Phi", hidden=True, clock_delta=1. / 10.)

# Running node
node_agent.run()
