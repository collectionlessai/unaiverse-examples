from unaiverse.agent import Agent
from unaiverse.streams import StreamType
from unaiverse.modules.networks import ViT
from unaiverse.networking.node.node import Node

# Agent
net = ViT()
agent = Agent(proc=net,
              proc_inputs=[StreamType(data_type="img", pubsub=False, private_only=True)],
              proc_outputs=[StreamType(data_type="tensor", tensor_dtype="torch.float32",
                                       tensor_shape=(None, len(net.labels)), tensor_labels=net.labels,
                                       pubsub=False, private_only=True)])

# Node hosting agent
node = Node(agent, node_name="ViT", hidden=True, clock_delta=1. / 15.)

# Running node
node.run(join_world="InfoExtraction")
