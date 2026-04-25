import os
import torch
import importlib.util
from unaiverse.agent import Agent
from unaiverse.streams import StreamType
from unaiverse.modules.networks import CNN
from unaiverse.networking.node.node import Node
from unaiverse.modules.utils import error_rate_mnist_test_set
from unaiverse.utils.misc import countdown_start, countdown_wait

# Creating neural network
net = CNN(d_dim=10, in_channels=1, seed=62)
net.transforms = lambda x: x  # Processing tensor data

# proc_opts must live on the CNN (which IS a ModuleWrapper) so that learn_backward() can see them
proc_opts = {'optimizer': torch.optim.SGD(net.parameters(), lr=0.05),
             'losses': [torch.nn.functional.cross_entropy]}
net.proc_opts = proc_opts

# Agent
agent = Agent(proc=net,
              proc_inputs=[StreamType(data_type="tensor", tensor_shape=(None, 1, 28, 28), tensor_dtype=torch.float32,
                                     pubsub=False, private_only=True)],
              proc_outputs=[StreamType(data_type="tensor", tensor_shape=(None,), tensor_dtype=torch.long,
                                      pubsub=False, private_only=True,
                                      proc_to_stream_transforms=lambda x: torch.argmax(x, dim=1))],
              proc_opts=proc_opts,
              buffer_generated_by_others="none")

# Node hosting agent
node = Node(node_name="Student", hosted=agent, hidden=True, clock_delta=1./10.)


# Starting countdown

# Running node
node.run(join_world="Class Incremental World")
