from unaiverse.agent import Agent
from unaiverse.dataprops import Data4Proc
from unaiverse.modules.networks import ViT
from unaiverse.networking.node.node import Node

# Agent
net = ViT()
agent = Agent(proc=net,
              proc_inputs=[Data4Proc(data_type="img", pubsub=False, private_only=True)],
              proc_outputs=[Data4Proc(data_type="tensor", tensor_dtype="torch.float32",
                                      tensor_shape=(None, len(net.labels)), tensor_labels=net.labels,
                                      pubsub=False, private_only=True)])

# Node hosting agent
node = Node(node_name="ViT", hosted=agent, hidden=True, clock_delta=1. / 10.)

# Telling agent to join world
node.ask_to_join_world(node_name="InfoExtraction")

# Running node
node.run()
