from unaiverse.agent import Agent
from unaiverse.networking.node.node import Node

# Agent
agent = Agent(proc=None, buffer_generated_by_others="one")

# Node hosting agent
node = Node(node_name="DigitClassifier1", hosted=agent, hidden=True, clock_delta=1. / 10.)

# Telling agent to join world
node.ask_to_join_world(node_name="DigitSocialLearning")

# Running node
node.run()
