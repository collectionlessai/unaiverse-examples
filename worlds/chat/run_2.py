from unaiverse.agent import Agent
from unaiverse.streams.dataprops import Data4Proc
from unaiverse.modules.networks import Phi
from unaiverse.networking.node.node import Node

# Agent
agent = Agent(proc=Phi(),
              proc_inputs=[Data4Proc(data_type="text", pubsub=False, private_only=False)],
              proc_outputs=[Data4Proc(data_type="text", pubsub=False, private_only=False)],
              proc_opts={})

# Node hosting agent
node = Node(node_name="ChatAI", hosted=agent, hidden=True, clock_delta=1. / 10.)

# Running node
node.run(join_world="ChatRoom")
