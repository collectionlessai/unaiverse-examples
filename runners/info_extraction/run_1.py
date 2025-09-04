import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from unaiverse.agent import Agent
from unaiverse.dataprops import Data4Proc
from unaiverse.networking.node.node import Node
from unaiverse.library.modules.networks import ViT
from unaiverse.utils.misc import get_node_addresses_from_file

# agent (ViT)
net = ViT()
agent = Agent(proc=net,
              proc_inputs=[Data4Proc(data_type="img", pubsub=False, private_only=True)],
              proc_outputs=[Data4Proc(data_type="tensor", tensor_dtype="torch.float32",
                                      tensor_shape=(None, len(net.labels)), tensor_labels=net.labels,
                                      pubsub=False, private_only=True)])

# node hosting agent
node = Node(node_id="02822e3961df4b6b9f9c6e6eeb4f7f73",
            password="password", hosted=agent, clock_delta=1. / 10.)

# telling agent to join world
node.ask_to_join_world(addresses=get_node_addresses_from_file(os.path.dirname(__file__)))

# running node
node.run()
