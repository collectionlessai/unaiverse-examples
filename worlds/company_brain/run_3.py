from unaiverse.agent import Agent
from unaiverse.networking.node.node import Node
from unaiverse.modules.networks import TinyLLama

# Agent
agent = Agent(proc=TinyLLama(), proc_inputs=["text"], proc_outputs=["text"])

# Node hosting agent
node = Node(agent, node_name="Expert", hidden=True, clock_delta=1. / 20.)

# Running node
node.run(join_world="CompanyBrain")
