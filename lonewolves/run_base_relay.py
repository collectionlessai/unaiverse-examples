from unaiverse.agent import Agent
from unaiverse.dataprops import Data4Proc
from unaiverse.networking.node.node import Node

# Agent
agent = Agent(proc=None,
              proc_inputs=[Data4Proc(data_type="text", pubsub=False, private_only=True)],
              proc_outputs=[Data4Proc(data_type="text", pubsub=False, private_only=True)])

# Node hosting agent
node = Node(node_name="BaseRelay", hosted=agent, clock_delta=1. / 10., save_checkpoint_every=-1.)

# Running node
# ALWAYS RUN THIS WITH THE FOLLOWING CONFIGURATION:
#   NODE_IS_ISOLATED=1
#   NODE_IS_PUBLIC=1
#   NODE_IS_PUBLIC_RELAY=1
#   NODE_USE_TLS=1
#   NODE_STARTING_PORT=30500
node.run()
