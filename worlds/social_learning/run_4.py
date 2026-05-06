import torch
from unaiverse.agent import Agent
from unaiverse.modules.networks import CNN
from unaiverse.networking.node.node import Node
from unaiverse.streams.dataprops import StreamType

# Agent
net = CNN(d_dim=10, in_channels=1, seed=62)
net.transforms = lambda x: x  # Processing tensor data
agent = Agent(proc=net,
              proc_inputs=[StreamType(data_type="tensor", tensor_shape=(None, 1, 28, 28), tensor_dtype=torch.float32,
                                      pubsub=False, private_only=True)],
              proc_outputs=[StreamType(data_type="tensor", tensor_shape=(None,), tensor_dtype=torch.long,
                                       pubsub=False, private_only=True,
                                       proc_to_stream_transforms=lambda x: torch.argmax(x, dim=1))],
              proc_opts={'optimizer': torch.optim.Adam(net.parameters(), lr=0.005),
                         'losses': [torch.nn.functional.cross_entropy]},
              buffer_generated_by_others="none")

# Node hosting agent
node = Node(agent, node_name="DigitClassifier4", hidden=True, clock_delta=1. / 15.)

# Running node (with role suggestions)
node.run(join_world="DigitSocialLearning", role_preference="student_isolated", resume_from_checkpoint=True)
