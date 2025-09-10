import torch
from unaiverse.agent import Agent
from unaiverse.dataprops import Data4Proc
from unaiverse.modules.networks import CNN
from unaiverse.networking.node.node import Node

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

# Node hosting agent
node = Node(node_name="DigitClassifier4", hosted=agent, hidden=True, clock_delta=1. / 10.)

# Telling agent to join world
node.ask_to_join_world(node_name="DigitSocialLearning", role_preference="student_isolated")  # Role suggestion

# Running node
node.run()
