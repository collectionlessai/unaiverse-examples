from unaiverse.agent import Agent
from unaiverse.dataprops import Data4Proc
from unaiverse.networking.node.node import Node
from unaiverse.modules.networks import TinyLLama

# Agent
agent = Agent(proc=TinyLLama(),
              proc_inputs=[Data4Proc(data_type="text", pubsub=False, private_only=False)],
              proc_outputs=[Data4Proc(data_type="text", pubsub=False, private_only=False)],
              proc_opts={})

# Node hosting agent
node_agent = Node(node_name="TinyLLama", hosted=agent, hidden=True, clock_delta=1. / 10.)

# Running node
node_agent.run()
