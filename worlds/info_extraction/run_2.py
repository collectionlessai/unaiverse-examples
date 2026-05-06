from unaiverse.agent import Agent
from unaiverse.streams import StreamType
from unaiverse.modules.networks import SmolVLM
from unaiverse.networking.node.node import Node

# Agent
agent = Agent(proc=SmolVLM(),
              proc_inputs=[StreamType(data_type="img", pubsub=False, private_only=False),
                           StreamType(data_type="text", pubsub=False, private_only=False)],
              proc_outputs=[StreamType(data_type="text", pubsub=False, private_only=False)],
              proc_opts={})

# Node hosting agent
node = Node(agent, node_name="SmolVLM", hidden=True, clock_delta=1. / 15.)

# Running node
node.run(join_world="InfoExtraction")
