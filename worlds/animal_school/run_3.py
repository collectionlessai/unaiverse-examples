import torch
from unaiverse.agent import Agent
from unaiverse.streams import StreamType
from unaiverse.modules.networks import CNN
from unaiverse.networking.node.node import Node

# Agent (plain CNN student)
net = CNN(3, seed=42)
assert isinstance(net.module, torch.nn.Module)

agent = Agent(proc=net,
              proc_opts={'optimizer': torch.optim.SGD(net.module.parameters(), lr=0.0025),
                         'losses': [torch.nn.functional.binary_cross_entropy]},
              buffer_generated_by_others="all")

# Setting textual labels to the different possible output classes
assert isinstance(agent.proc_outputs, list)
out = agent.proc_outputs[0]
assert isinstance(out, StreamType)
out.set_tensor_labels(["albatross", "cheetah", "giraffe"])

# Node hosting agent
node = Node(node_name="Test3", hosted=agent, hidden=True, clock_delta=1. / 100.)

# Running node
node.run(join_world="AnimalSchool")
