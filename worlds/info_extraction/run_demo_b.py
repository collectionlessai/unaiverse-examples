import os
import sys
from unaiverse.agent import Agent
from unaiverse.dataprops import Data4Proc
from unaiverse.networking.node.node import Node
from unaiverse.modules.networks import FasterRCNN
from unaiverse.utils.misc import get_node_addresses_from_file

# agent (FasterRCNN)
agent = Agent(proc=FasterRCNN(),
              proc_inputs=[Data4Proc(data_type="img", pubsub=False, private_only=True)],
              proc_outputs=[Data4Proc(data_type="tensor", tensor_dtype="torch.long", tensor_shape=(None,),
                                      pubsub=False, private_only=True),
                            Data4Proc(data_type="tensor", tensor_dtype="torch.float32", tensor_shape=(None,),
                                      pubsub=False, private_only=True),
                            Data4Proc(data_type="tensor", tensor_dtype="torch.float32", tensor_shape=(None, 4),
                                      pubsub=False, private_only=True),
                            Data4Proc(data_type="text", pubsub=False, private_only=True)],
              proc_opts={})

# node hosting agent
node = Node(node_id="337a5f4ccc274d2b95a472c616baf010",
            password="password", hosted=agent, clock_delta=1. / 10.)

# telling agent to join world
node.ask_to_join_world(addresses=get_node_addresses_from_file(os.path.dirname(__file__)))

# running node
node.run()
