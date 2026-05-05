from unaiverse.agent import Agent
from unaiverse.networking.node.node import Node
from unaiverse.modules.networks import TinyLLama

# Agent
agent = Agent(proc=TinyLLama(), proc_inputs=["text"], proc_outputs=["text"])

# Node hosting agent
node_agent = Node(agent, node_name="TinyLLama", hidden=True, clock_delta=1. / 10.)

# Running node
node_agent.run()
