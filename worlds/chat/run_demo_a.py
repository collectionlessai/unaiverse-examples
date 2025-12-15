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

# Running node
node.run(join_world="ChatRoom", interact_mode=True)
