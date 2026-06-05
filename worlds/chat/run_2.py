from unaiverse.agent import Agent
from unaiverse.modules.networks import Phi
from unaiverse.networking.node.node import Node

# Agent (AI user: text-in, text-out via Phi)
agent = Agent(proc=Phi(), proc_inputs=["text"], proc_outputs=["text"])

# Node hosting agent
node = Node(agent, node_name="ChatAI", hidden=True, clock_delta=1. / 25.)

# Running node
node.run(join_world="ChatRoom")
