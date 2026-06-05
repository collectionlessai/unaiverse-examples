from unaiverse.agent import Agent
from unaiverse.networking.node.node import Node
from unaiverse.streams.dataprops import StreamType

# Agent (broadcaster: proc=None, declared text I/O slots for stream matching)
agent = Agent(proc=None,
              proc_inputs=[StreamType(data_type="text", private_only=True)],
              proc_outputs=[StreamType(data_type="text", private_only=True)])

# Node hosting agent
node = Node(agent, node_name="Broadcaster", hidden=True, clock_delta=1. / 20.)

# Running node
node.run(join_world="ChatRoom")
