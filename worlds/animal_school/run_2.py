import torch
from unaiverse.agent import Agent
from unaiverse.streams import StreamType
from unaiverse.modules.networks import CNNCNU
from unaiverse.networking.node.node import Node

# Agent (CNN+CNU student)
net = CNNCNU(3, cnu_memories=5, seed=42)
assert isinstance(net.module, torch.nn.Module)

agent = Agent(proc=net,
              proc_opts={
                  'optimizer': torch.optim.SGD([
                      {'params': net.module[:-2].parameters(), 'lr': 0.0001},
                      {'params': net.module[-2:].parameters(), 'lr': 0.005}],
                      lr=0.0001),
                  'losses': [torch.nn.functional.binary_cross_entropy]
              },
              buffer_generated_by_others="all")

# Setting textual labels to the different possible output classes
assert isinstance(agent.proc_outputs, list)
out = agent.proc_outputs[0]
assert isinstance(out, StreamType)
out.set_tensor_labels(["albatross", "cheetah", "giraffe"])

# Node hosting agent
node = Node(node_name="Test2", hosted=agent, hidden=True, clock_delta=1. / 100.)

# Running node
node.run(join_world="AnimalSchool")
