from unaiverse.agent import Agent
from unaiverse.networking.node.node import Node

# Agent
agent = Agent(proc=None, buffer_generated_by_others="one")

# Node hosting agent
node = Node(agent, node_name="DigitClassifier1", hidden=True, clock_delta=1. / 15.)

# Running node
node.run(join_world="DigitSocialLearning")
