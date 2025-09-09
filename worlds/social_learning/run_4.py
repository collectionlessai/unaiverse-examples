import os
import torch
from unaiverse.agent import Agent
from unaiverse.dataprops import Data4Proc
from unaiverse.modules.networks import CNN
from unaiverse.networking.node.node import Node
from unaiverse.utils.misc import get_node_addresses_from_file

# Agent (student 3)
net = CNN(d_dim=10, in_channels=1, seed=62)
net.transforms = lambda x: x  # Processing tensor data
agent = Agent(proc=net,
              proc_inputs=[Data4Proc(data_type="tensor", tensor_shape=(None, 1, 28, 28), tensor_dtype=torch.float32,
                                     pubsub=False, private_only=True)],
              proc_outputs=[Data4Proc(data_type="tensor", tensor_shape=(None,), tensor_dtype=torch.long,
                                      pubsub=False, private_only=True,
                                      proc_to_stream_transforms=lambda x: torch.argmax(x, dim=1))],
              proc_opts={'optimizer': torch.optim.Adam(net.parameters(), lr=0.005),
                         'losses': [torch.nn.functional.cross_entropy]},
              buffer_generated_by_others="none")

# TODO replace node_id="..." with node_name="DigitClassifier4"
# Node hosting agent
node = Node(node_id="70e94a785ccf428cb7934a203b3134b0", unaiverse_key="<UNAIVERSE_KEY_GOES_HERE>", hidden=True,
            hosted=agent, clock_delta=1. / 10.)

# Telling agent to join world
node.ask_to_join_world(addresses=get_node_addresses_from_file(os.path.dirname(__file__)),
                       role_preference="student_isolated")  # role suggestion

# Running node
node.run()
