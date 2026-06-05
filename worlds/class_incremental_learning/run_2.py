import torch
from unaiverse.agent import Agent
from unaiverse.streams import StreamType
from unaiverse.modules.networks import CNNMNIST
from unaiverse.networking.node.node import Node

# Neural network
net = CNNMNIST(d_dim=10, seed=62)  # CNN pre-configured for MNIST (in_channels=1, in_res=28)
assert isinstance(net.module, torch.nn.Module)
proc_inputs = [StreamType(data_type="tensor", tensor_shape=(None, 1, 28, 28), tensor_dtype=torch.float32,
                          private_only=True)]
proc_outputs = [StreamType(data_type="tensor", tensor_shape=(None,), tensor_dtype=torch.long,
                           private_only=True, proc_to_stream_transforms=lambda x: torch.argmax(x, dim=1))]
proc_opts = {'optimizer': torch.optim.SGD(net.module.parameters(), lr=0.05),
             'losses': [torch.nn.functional.cross_entropy]}

# Agent
agent = Agent(proc=net, proc_inputs=proc_inputs, proc_outputs=proc_outputs, proc_opts=proc_opts)

# Node hosting the student agent
node = Node(node_name="Test2", hosted=agent, hidden=True, clock_delta=1./10.)

# Running node
node.run(join_world="ClassIncrementalWorld")
