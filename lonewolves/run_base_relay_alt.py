from unaiverse.agent import Agent
from unaiverse.custom import Custom
from unaiverse.streams import StreamType
from unaiverse.networking.node.node import Node

# Options (key options for relay nodes)
Custom.ENV_IS_ISOLATED = True
Custom.ENV_IS_PUBLIC = True
Custom.ENV_IS_PUBLIC_RELAY = True
Custom.ENV_USE_TLS = True

# Agent
agent = Agent(proc=None,
              proc_inputs=[StreamType(data_type="text", private_only=True)],
              proc_outputs=[StreamType(data_type="text", private_only=True)])

# Node hosting agent
node = Node(node_name="BaseRelayAlt", hosted=agent, clock_delta=1. / 25., save_checkpoint_every=-1.)

# Running node
node.run()
