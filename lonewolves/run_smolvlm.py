from unaiverse.agent import Agent
from unaiverse.dataprops import Data4Proc
from unaiverse.modules.networks import SmolVLM
from unaiverse.networking.node.node import Node

# Agent
agent = Agent(proc=SmolVLM(),
              proc_inputs=[Data4Proc(data_type="img", pubsub=False, private_only=False),
                           Data4Proc(data_type="text", pubsub=False, private_only=False)],
              proc_outputs=[Data4Proc(data_type="text", pubsub=False, private_only=False)],
              proc_opts={})

# Node hosting agent
node_agent = Node(node_name="SmolVLM", hosted=agent, hidden=True, clock_delta=1. / 10.)

# Running node
node_agent.run()
