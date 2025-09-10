from unaiverse.agent import Agent
from unaiverse.dataprops import Data4Proc
from unaiverse.networking.node.node import Node

# Agent
agent = Agent(proc=None,
              proc_inputs=[Data4Proc(data_type="text", pubsub=False, private_only=True)],
              proc_outputs=[Data4Proc(data_type="text", pubsub=False, private_only=True)],
              proc_opts={})

# Node hosting agent
node = Node(node_name="Test0", hosted=agent, hidden=True, clock_delta=1. / 10.)

# Telling agent to join world
node.ask_to_join_world(node_name="ChatRoom")

# Running node
node.run(interact_mode_opts={})  # The presence of "interact_mode_opts" tells we want to jump into the interactive mode
