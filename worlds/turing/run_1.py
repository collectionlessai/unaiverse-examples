from unaiverse.agent import Agent
from unaiverse.streams.dataprops import Data4Proc
from unaiverse.networking.node.node import Node

# Agent
agent = Agent(proc=None,
              proc_inputs=[Data4Proc(data_type="text", pubsub=False, private_only=True)],
              proc_outputs=[Data4Proc(data_type="text", pubsub=False, private_only=True)])  # Also switch to pubsub=True

# Node hosting agent
node = Node(node_name="TuringManager", hosted=agent, hidden=True, clock_delta=1. / 50.)

# Running node
node.run(join_world="TuringHotel")
